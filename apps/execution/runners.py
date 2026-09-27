"""Language runners.

A runner turns (user source, problem) into files on disk, compiles them once and
knows how to launch the resulting program.  Registering a language therefore
means: add a ``Language`` row and (optionally) a runner class here.
"""

from __future__ import annotations

import logging
import os
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

from . import harness, sandbox

logger = logging.getLogger("dsa.execution")


@dataclass
class Build:
    ok: bool
    files: dict = field(default_factory=dict)
    error: str = ""
    output: str = ""
    run_argv: list = field(default_factory=list)
    workdir: Path | None = None


class BaseRunner:
    """Interpreted languages: nothing to compile."""

    name = "script"
    entry_file = "main"

    def __init__(self, language, workdir: Path):
        self.language = language
        self.workdir = workdir
        self.settings = settings

    # -- to override --------------------------------------------------------
    def render(self, source: str, problem) -> dict:
        return {"main": harness.render(self.language.slug, source, problem)}

    def compile(self, files: dict) -> tuple[bool, str, str]:
        return True, "", ""

    def argv(self, files: dict) -> list:
        raise NotImplementedError

    def memory_limit_mb(self) -> int:
        return self.language.memory_limit_mb

    def use_rlimit_as(self) -> bool:
        return self.language.enforce_address_space_limit

    def time_limit(self) -> float:
        return self.language.time_limit

    def run_env(self) -> dict:
        return dict(self.language.run_env or {})

    def image(self) -> str | None:
        if self.settings.DSA_EXECUTION_BACKEND == "docker":
            return self.language.docker_image or self.settings.DSA_DOCKER_IMAGE
        return None

    # -- shared -------------------------------------------------------------
    def build(self, source: str, problem) -> Build:
        try:
            files = self.render(source, problem)
        except ValueError as exc:
            return Build(ok=False, error=str(exc))
        if isinstance(files, str):
            files = {"main": files}
        sandbox.write_files(self.workdir, files)
        ok, error, output = self.compile(files)
        if not ok:
            return Build(ok=False, error=error, output=output, files=files)
        return Build(ok=True, files=files, output=output, run_argv=self.argv(files), workdir=self.workdir)

    def cleanup(self) -> None:
        pass


class PythonRunner(BaseRunner):
    name = "python"

    def render(self, source, problem):
        return {"main.py": harness.render("python", source, problem)}

    def argv(self, files):
        return [sandbox.default_python(), "-I", "-B", "main.py"]


class JavaScriptRunner(BaseRunner):
    name = "javascript"

    def render(self, source, problem):
        return {"main.js": harness.render("javascript", source, problem)}

    def argv(self, files):
        node = shutil_which("node") or "node"
        return [node, "main.js"]

    def use_rlimit_as(self):
        # V8 reserves a large virtual address space; rely on the heap cap.
        return False

    def memory_limit_mb(self):
        return max(self.language.memory_limit_mb, 512)


class CppRunner(BaseRunner):
    name = "cpp"
    compiler_var = "DSA_CXX"

    def render(self, source, problem):
        return {"main.cpp": harness.render("cpp", source, problem)}

    def compile(self, files):
        compiler = os.environ.get(self.compiler_var) or shutil_which("g++") or "g++"
        cmd = [compiler, "main.cpp", "-O2", "-std=c++17", "-o", "program", "-w"]
        result = sandbox.run_process(
            cmd,
            cwd=self.workdir,
            timeout=self.language.compile_timeout,
            memory_mb=max(self.language.memory_limit_mb, 1024),
            use_rlimit_as=True,
        )
        if result.error:
            return False, result.error, result.stdout + result.stderr
        if result.exit_code != 0:
            return False, "compilation failed", (result.stdout + result.stderr).strip()
        return True, "", result.stderr.strip()

    def argv(self, files):
        return ["./program"]

    def cleanup(self):
        binary = self.workdir / "program"
        if binary.exists():
            try:
                binary.chmod(0o755)
            except OSError:
                pass


class CRunner(CppRunner):
    name = "c"
    compiler_var = "DSA_CC"

    def render(self, source, problem):
        return {"main.c": harness.render("c", source, problem)}

    def compile(self, files):
        compiler = os.environ.get(self.compiler_var) or shutil_which("gcc") or "gcc"
        cmd = [compiler, "main.c", "-O2", "-std=c11", "-o", "program", "-w", "-lm"]
        result = sandbox.run_process(
            cmd,
            cwd=self.workdir,
            timeout=self.language.compile_timeout,
            memory_mb=max(self.language.memory_limit_mb, 1024),
            use_rlimit_as=True,
        )
        if result.error:
            return False, result.error, result.stdout + result.stderr
        if result.exit_code != 0:
            return False, "compilation failed", (result.stdout + result.stderr).strip()
        return True, "", result.stderr.strip()


class JavaRunner(BaseRunner):
    name = "java"

    def render(self, source, problem):
        files = harness.render("java", source, problem)
        return dict(files)

    def compile(self, files):
        javac = shutil_which("javac") or "javac"
        cmd = [javac, "-encoding", "UTF-8", "-nowarn", *files.keys()]
        result = sandbox.run_process(
            cmd,
            cwd=self.workdir,
            timeout=self.language.compile_timeout,
            memory_mb=max(self.language.memory_limit_mb, 1024),
            use_rlimit_as=False,
        )
        if result.error:
            return False, result.error, result.stdout + result.stderr
        if result.exit_code != 0:
            return False, "compilation failed", (result.stdout + result.stderr).strip()
        return True, "", result.stderr.strip()

    def argv(self, files):
        java = shutil_which("java") or "java"
        heap = max(128, self.memory_limit_mb() - 128)
        return [
            java,
            "-XX:+UseSerialGC",
            "-Xshare:auto",
            f"-Xmx{heap}m",
            "-Xss64m",
            "-Dfile.encoding=UTF-8",
            self.entry_class(files),
        ]

    @staticmethod
    def entry_class(files) -> str:
        """``Main`` for function mode, otherwise the user's own public class."""
        if "Main.java" in files:
            return "Main"
        for name in files:
            if name.endswith(".java"):
                return name[: -len(".java")]
        return "Main"

    def use_rlimit_as(self):
        return False

    def memory_limit_mb(self):
        return max(self.language.memory_limit_mb, 1024)

    def cleanup(self):
        for cls in self.workdir.glob("*.class"):
            try:
                cls.unlink()
            except OSError:
                pass


class ScriptRunner(BaseRunner):
    """Generic fallback driven purely by the Language row's command templates."""

    name = "script"

    def render(self, source, problem):
        extension = self.language.file_extension or ".txt"
        return {f"main{extension}": source}

    def compile(self, files):
        command = (self.language.compile_command or "").strip()
        if not command:
            return True, "", ""
        argv = [self._expand(part, files, "out") for part in shlex.split(command)]
        result = sandbox.run_process(
            argv,
            cwd=self.workdir,
            timeout=self.language.compile_timeout,
            memory_mb=max(self.language.memory_limit_mb, 1024),
        )
        if result.error:
            return False, result.error, result.stdout + result.stderr
        if result.exit_code != 0:
            return False, "compilation failed", (result.stdout + result.stderr).strip()
        return True, "", result.stderr.strip()

    def argv(self, files):
        command = (self.language.execution_command or "").strip()
        if not command:
            return ["./main"]
        extension = self.language.file_extension or ""
        return [self._expand(part, files, None) for part in shlex.split(command)]

    def _expand(self, token: str, files: dict, out_name: str | None) -> str:
        main = f"main{self.language.file_extension or ''}"
        return (
            token.replace("{file_name}", main)
            .replace("{file}", str(self.workdir / main))
            .replace("{dir}", str(self.workdir))
            .replace("{python}", sandbox.default_python())
            .replace("{out}", str(self.workdir / (out_name or "program")))
        )


RUNNERS = {
    "python": PythonRunner,
    "javascript": JavaScriptRunner,
    "cpp": CppRunner,
    "c": CRunner,
    "java": JavaRunner,
    "script": ScriptRunner,
}


def get_runner(language, workdir: Path) -> BaseRunner:
    runner_class = RUNNERS.get(getattr(language, "runner", "") or "script", ScriptRunner)
    return runner_class(language, workdir)


def shutil_which(binary: str) -> str | None:
    import shutil

    return shutil.which(binary) or _which_fallback(binary)


def _which_fallback(binary: str) -> str | None:
    """Extra lookup for JDK tools that are not always on PATH."""
    candidates = {
        "node": ["/usr/bin/node", "/usr/local/bin/node", "/opt/node/bin/node"],
        "java": ["/usr/bin/java"],
        "javac": ["/usr/bin/javac"],
    }
    for path in candidates.get(binary, []):
        if os.path.exists(path):
            return path
    return None
