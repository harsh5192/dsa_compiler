"""Process isolation for user-submitted code.

Design goals, in order of importance:

1. **Never run inside the Django process.**  Everything happens in a child
   process started from a throw-away working directory.
2. **Bounded resources.**  CPU rlimit, wall-clock timeout, address-space rlimit,
   file-size rlimit, process-count rlimit and output capture limits.
3. **No ambient authority.**  The child gets a scrubbed environment, a fresh
   working directory that is deleted afterwards, and (on Linux) no ability to
   reach the database or app secrets because it simply has no paths to them.
4. **Killable.**  The child runs in its own session; a timeout kills the whole
   process group so runaway threads/children die too.

Two backends are available:

``subprocess``
    The default.  No extra dependencies, works everywhere, and is appropriate
    for a single-user laptop.  It is *not* a security boundary against a
    determined attacker.

``docker``
    Opt in with ``DSA_EXECUTION_BACKEND=docker``.  Much stronger isolation
    (no network, memory cap, read-only mount) at the cost of requiring the
    docker CLI and per-language images.

Arbitrary code execution is inherently security sensitive.  See the
"Code execution setup" section of README.md before exposing this app to
anything but yourself.
"""

from __future__ import annotations

import logging
import os
import resource
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

logger = logging.getLogger("dsa.execution")


@dataclass
class ProcessResult:
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    max_rss_bytes: int = 0
    timed_out: bool = False
    killed_by_signal: int | None = None
    truncated: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.error


@dataclass
class BuildResult:
    ok: bool
    error: str = ""
    output: str = ""
    workdir: Path | None = None
    files: dict = field(default_factory=dict)


def default_python() -> str:
    return sys.executable or "python3"


def _make_preexec(cpu_seconds: int, memory_mb: int, use_rlimit_as: bool):
    """Build the child-side resource limiter (POSIX only)."""

    def preexec() -> None:  # pragma: no cover - runs in the forked child
        os.setsid()
        try:
            if use_rlimit_as and memory_mb:
                limit = memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            target = 256
            if hard == resource.RLIM_INFINITY or hard > target:
                resource.setrlimit(resource.RLIMIT_NOFILE, (target, target))
        except (ValueError, OSError):
            pass
        try:
            os.nice(5)
        except OSError:
            pass

    return preexec


def _popen_supported() -> bool:
    return hasattr(os, "setsid") and hasattr(resource, "setrlimit")


def run_process(
    command: list[str],
    *,
    cwd: Path,
    stdin_data: str = "",
    timeout: float = 5.0,
    memory_mb: int = 512,
    use_rlimit_as: bool = True,
    env: dict | None = None,
    image: str | None = None,
    output_limit: int | None = None,
) -> ProcessResult:
    """Run ``command`` under time and memory limits and capture its output."""
    if output_limit is None:
        output_limit = getattr(settings, "DSA_OUTPUT_LIMIT", 512 * 1024)

    cpu_seconds = max(1, int(timeout) + 1)
    preexec = _make_preexec(cpu_seconds, memory_mb, use_rlimit_as) if _popen_supported() else None

    docker_mode = bool(image)
    if docker_mode:
        command = [
            "docker", "run", "--rm", "--interactive",
            "--network", "none",
            "--memory", f"{max(memory_mb, 64)}m",
            "--memory-swap", f"{max(memory_mb, 64)}m",
            "--pids-limit", "64",
            "--cpus", "1",
            "--volume", f"{cwd}:/work:ro",
            "--workdir", "/work",
            image,
        ] + list(command)

    child_env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(cwd),
        "TMPDIR": str(cwd),
        "LANG": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NODE_OPTIONS": "--max-old-space-size=256",
    }
    if env:
        child_env.update({str(k): str(v) for k, v in env.items()})

    start = time.perf_counter()
    result = ProcessResult()
    proc = None
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_env,
            preexec_fn=preexec,
            close_fds=True,
        )
    except FileNotFoundError as exc:
        result.error = f"Toolchain not found: {command[0]}"
        logger.warning("execution toolchain missing: %s", exc)
        return result
    except OSError as exc:
        result.error = f"Could not start the sandbox process: {exc}"
        logger.warning("could not start sandbox: %s", exc)
        return result

    try:
        payload = (stdin_data or "").encode("utf-8", "replace")
        try:
            proc.stdin.write(payload)
        except (BrokenPipeError, OSError):
            pass
        try:
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

        stdout_chunks, stderr_chunks = [], []
        total = 0
        streams = {}
        if proc.stdout is not None:
            streams[proc.stdout.fileno()] = (proc.stdout, stdout_chunks)
        if proc.stderr is not None:
            streams[proc.stderr.fileno()] = (proc.stderr, stderr_chunks)

        deadline = start + timeout
        open_fds = set(streams)
        while open_fds:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                result.timed_out = True
                break
            ready, _, _ = select.select(list(open_fds), [], [], min(0.2, remaining))
            for fd in ready:
                stream, sink = streams[fd]
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    chunk = b""
                if not chunk:
                    open_fds.discard(fd)
                    continue
                if total + len(chunk) > output_limit:
                    allowed = max(0, output_limit - total)
                    if allowed:
                        sink.append(chunk[:allowed])
                    result.truncated = True
                else:
                    sink.append(chunk)
                total += len(chunk)

        if result.timed_out:
            _terminate(proc)

        # Reap with wait4 so we get this child's rusage (peak RSS).  ``wait4``
        # only works while the child is still a zombie, so nothing above may
        # have reaped it: ``_terminate`` deliberately does not call ``wait``.
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except OSError:
            pass
        try:
            _, status, rusage = os.wait4(proc.pid, 0)
        except ChildProcessError:
            # Already reaped (a race with poll()): fall back to plain wait().
            proc.wait()
            status = proc.returncode << 8 if (proc.returncode or 0) >= 0 else 0
            rusage = None
        proc.returncode = os.waitstatus_to_exitcode(status)
        if os.WIFSIGNALED(status):
            result.killed_by_signal = os.WTERMSIG(status)
        result.exit_code = proc.returncode
        if rusage is not None:
            result.max_rss_bytes = 0 if docker_mode else int(rusage.ru_maxrss) * 1024
        result.stdout = b"".join(stdout_chunks).decode("utf-8", "replace")
        result.stderr = b"".join(stderr_chunks).decode("utf-8", "replace")
    except Exception as exc:  # pragma: no cover - defensive
        _terminate(proc)
        result.error = f"Sandbox failure: {exc}"
        logger.exception("sandbox failure")
    finally:
        result.duration = time.perf_counter() - start
        for stream in (proc.stdout, proc.stderr, proc.stdin):
            try:
                if stream and not stream.closed:
                    stream.close()
            except OSError:
                pass
    return result


def _terminate(proc) -> None:
    """Kill the child's process group without reaping it.

    ``run_process`` reaps with ``wait4`` afterwards to collect rusage, so this
    must not call ``proc.wait()``/``proc.poll()`` first: either one would reap
    the child and make the later ``wait4`` fail.
    """
    if proc is None or proc.returncode is not None:
        return
    for sig in (signal.SIGKILL,):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass


def work_root() -> Path:
    root = Path(getattr(settings, "DSA_WORK_DIR", tempfile.gettempdir())) / "run"
    root.mkdir(parents=True, exist_ok=True)
    return root


def make_workdir(prefix: str = "job") -> Path:
    return Path(tempfile.mkdtemp(prefix=f"{prefix}_", dir=str(work_root())))


def cleanup_workdir(path: Path | None) -> None:
    if not path:
        return
    shutil.rmtree(path, ignore_errors=True)


def write_files(workdir: Path, files: dict) -> None:
    for name, content in files.items():
        target = workdir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
