"""The execution service.

This is the only module that orchestrates compile + run + judge.  Views and API
endpoints call :func:`execute` and then persist the result; they never touch
subprocesses directly.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from . import runners, sandbox
from .checkers import CheckerError, outputs_match_checked
from .compare import format_output, outputs_match

logger = logging.getLogger("dsa.execution")

VERDICT_ACCEPTED = "accepted"
VERDICT_WRONG_ANSWER = "wrong_answer"
VERDICT_COMPILE_ERROR = "compilation_error"
VERDICT_RUNTIME_ERROR = "runtime_error"
VERDICT_TLE = "time_limit_exceeded"
VERDICT_MLE = "memory_limit_exceeded"
VERDICT_EMPTY = "empty_submission"
VERDICT_INTERNAL = "internal_error"

HARD_FAILURES = {VERDICT_TLE, VERDICT_MLE, VERDICT_RUNTIME_ERROR}

_RUNTIME_MARKERS = (
    "runtimeerror",
    "segmentation fault",
    "index out of range",
    "traceback",
    "exception",
    "nullpointerexception",
    "abort",
    "fatal",
)


@dataclass
class CaseResult:
    label: str
    input_data: str
    expected_output: str
    actual_output: str = ""
    verdict: str = VERDICT_INTERNAL
    execution_time: float = 0.0
    memory_used: int = 0
    error: str = ""
    is_sample: bool = False
    is_custom: bool = False
    test_case: object = None


@dataclass
class ExecutionReport:
    verdict: str = VERDICT_INTERNAL
    cases: list = field(default_factory=list)
    total_time: float = 0.0
    max_case_time: float = 0.0
    max_memory: int = 0
    compile_output: str = ""
    error_message: str = ""
    stdout: str = ""
    stderr: str = ""
    used_docker: bool = False

    @property
    def passed(self) -> int:
        return sum(1 for case in self.cases if case.verdict == VERDICT_ACCEPTED)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def accepted(self) -> bool:
        return self.verdict == VERDICT_ACCEPTED

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "test_cases_passed": self.passed,
            "total_test_cases": self.total,
            "execution_time": round(self.total_time, 4),
            "max_execution_time": round(self.max_case_time, 4),
            "memory_used": self.max_memory,
            "compile_output": self.compile_output,
            "error_message": self.error_message,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "used_docker": self.used_docker,
            "cases": [
                {
                    "label": case.label,
                    "input": case.input_data,
                    "expected_output": case.expected_output,
                    "actual_output": case.actual_output,
                    "verdict": case.verdict,
                    "execution_time": round(case.execution_time, 4),
                    "memory_used": case.memory_used,
                    "error": case.error,
                    "is_sample": case.is_sample,
                    "is_custom": case.is_custom,
                }
                for case in self.cases
            ],
        }


class ExecutionUnavailable(Exception):
    """Raised when the language toolchain is not installed on this machine."""


def _limits_for(language, problem) -> tuple[float, int, bool]:
    time_limit = problem.time_limit or language.time_limit or settings.DSA_TIME_LIMIT
    memory_mb = problem.memory_limit_mb or language.memory_limit_mb
    return float(time_limit), int(memory_mb), bool(language.enforce_address_space_limit)


def select_test_cases(problem, mode: str, custom_cases=None) -> list:
    """Choose which cases a Run / Submit should execute."""
    if mode == "run" and custom_cases:
        return list(custom_cases)
    if mode == "run":
        return [tc for tc in problem.test_cases.all() if tc.is_sample and not tc.is_hidden]
    return list(problem.test_cases.all())


def execute(
    *,
    problem,
    language,
    source_code: str,
    mode: str = "submit",
    custom_cases=None,
    workdir=None,
) -> ExecutionReport:
    """Compile and run ``source_code`` against the selected test cases."""
    report = ExecutionReport()

    if not (source_code or "").strip():
        report.verdict = VERDICT_EMPTY
        report.error_message = "Write some code before running."
        return report

    owns_workdir = workdir is None
    workdir = workdir or sandbox.make_workdir(prefix=f"p{getattr(problem, 'pk', 0)}")
    runner = runners.get_runner(language, workdir)
    time_limit, memory_mb, use_rlimit_as = _limits_for(language, problem)
    report.used_docker = settings.DSA_EXECUTION_BACKEND == "docker"

    try:
        build = runner.build(source_code, problem)
        if not build.ok:
            report.verdict = VERDICT_COMPILE_ERROR
            report.compile_output = format_output(build.output or build.error, 8000)
            report.error_message = _clean_compile_error(build.error, build.output)
            return report
        report.compile_output = format_output(build.output, 4000) if build.output else ""

        cases = select_test_cases(problem, mode, custom_cases)
        if not cases:
            report.verdict = VERDICT_INTERNAL
            report.error_message = (
                "This problem has no test cases yet. Add some in the admin panel "
                "or import them with a sheet."
            )
            return report

        batch_deadline = time.perf_counter() + settings.DSA_BATCH_TIME_LIMIT
        image = runner.image()
        for index, case in enumerate(cases):
            if time.perf_counter() > batch_deadline:
                report.cases.append(
                    CaseResult(
                        label=_case_label(case, index),
                        input_data=str(case_field(case, "input_data", "")),
                        expected_output=str(case_field(case, "expected_output", "")),
                        verdict=VERDICT_TLE,
                        error="Stopped early: the batch time budget was exhausted.",
                        is_sample=bool(case_field(case, "is_sample", False)),
                    )
                )
                break

            case_result = _run_one(
                runner=runner,
                argv=build.run_argv,
                case=case,
                index=index,
                time_limit=time_limit,
                memory_mb=memory_mb,
                use_rlimit_as=use_rlimit_as,
                image=image,
            )
            report.cases.append(case_result)
            report.total_time += case_result.execution_time
            report.max_case_time = max(report.max_case_time, case_result.execution_time)
            report.max_memory = max(report.max_memory, case_result.memory_used)
            if case_result.actual_output and not report.stdout:
                report.stdout = format_output(case_result.actual_output)
            if case_result.error and not report.stderr:
                report.stderr = format_output(case_result.error, 4000)
            if case_result.verdict in HARD_FAILURES:
                break

        report.verdict = _aggregate(report)
        # Surface the reason on the report itself so the UI (and the API) can
        # show it without walking the case list.
        if not report.error_message:
            for case_result in report.cases:
                if case_result.error:
                    report.error_message = case_result.error
                    break
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("execution failed")
        report.verdict = VERDICT_INTERNAL
        report.error_message = f"Internal execution error: {exc}"
    finally:
        runner.cleanup()
        if owns_workdir:
            sandbox.cleanup_workdir(workdir)
    return report


def case_field(case, name, default=""):
    """Read ``name`` from a :class:`TestCase` row *or* a plain dict.

    Custom cases typed into the browser arrive as dictionaries; stored cases
    arrive as model instances.  Both have to work here.
    """
    if isinstance(case, dict):
        value = case.get(name, default)
    else:
        value = getattr(case, name, default)
    return default if value is None else value


def _run_one(
    *, runner, argv, case, index, time_limit, memory_mb, use_rlimit_as, image
) -> CaseResult:
    result = CaseResult(
        label=_case_label(case, index),
        input_data=str(case_field(case, "input_data", "")),
        expected_output=str(case_field(case, "expected_output", "")),
        is_sample=bool(case_field(case, "is_sample", False)),
        is_custom=bool(case_field(case, "is_custom", False)),
        test_case=case if hasattr(case, "pk") else None,
    )

    proc = sandbox.run_process(
        argv,
        cwd=runner.workdir,
        stdin_data=result.input_data or "",
        timeout=time_limit,
        memory_mb=memory_mb,
        use_rlimit_as=use_rlimit_as,
        env=runner.run_env(),
        image=image,
    )
    result.execution_time = proc.duration
    result.memory_used = proc.max_rss_bytes
    result.actual_output = format_output(proc.stdout)

    if proc.error:
        result.verdict = VERDICT_INTERNAL
        result.error = proc.error
        return result

    if proc.timed_out or proc.killed_by_signal in (9, 24):
        result.verdict = VERDICT_TLE
        result.error = (
            f"Your program exceeded the {time_limit:g} second time limit."
        )
        return result

    if _looks_like_memory_failure(proc.stderr) or (proc.killed_by_signal == 9 and not proc.stdout):
        result.verdict = VERDICT_MLE
        result.error = f"Your program exceeded the {memory_mb} MB memory limit."
        return result

    if proc.exit_code != 0 or _runtime_markers(proc.stderr):
        result.verdict = VERDICT_RUNTIME_ERROR
        result.error = _clean_runtime_error(proc.stderr, proc.killed_by_signal)
        return result

    checker = str(case_field(case, "checker", "")).strip()
    if checker:
        matched = outputs_match_checked(
            proc.stdout,
            result.expected_output,
            checker,
            result.input_data,
        )
    else:
        matched = outputs_match(
            proc.stdout,
            result.expected_output,
            str(case_field(case, "comparison", "exact")),
        )
    if matched:
        result.verdict = VERDICT_ACCEPTED
    else:
        result.verdict = VERDICT_WRONG_ANSWER
    return result


def _case_label(case, index: int) -> str:
    label = str(case_field(case, "label", "")) or str(case_field(case, "name", ""))
    return label or f"Test case {index + 1}"


def _runtime_markers(stderr: str) -> bool:
    if not stderr:
        return False
    lowered = stderr.lower()
    if lowered.startswith("runtimeerror"):
        return True
    return any(marker in lowered for marker in _RUNTIME_MARKERS)


#: Messages that mean the sandbox really ran out of memory.  The patterns are
#: anchored on word boundaries on purpose: a plain "oom" substring also matches
#: innocent words such as "boom" or "groom".
MEMORY_FAILURE_PATTERNS = (
    re.compile(r"std::bad_alloc"),
    re.compile(r"out of memory"),
    re.compile(r"cannot allocate memory"),
    re.compile(r"\bMemoryError\b"),
    re.compile(r"\boom\b", re.IGNORECASE),
    re.compile(r"memory exhausted", re.IGNORECASE),
)


def _looks_like_memory_failure(stderr: str) -> bool:
    if not stderr:
        return False
    return any(pattern.search(stderr) for pattern in MEMORY_FAILURE_PATTERNS)


def _aggregate(report: ExecutionReport) -> str:
    if not report.cases:
        return VERDICT_INTERNAL
    for case in report.cases:
        if case.verdict in HARD_FAILURES:
            return case.verdict
    if all(case.verdict == VERDICT_ACCEPTED for case in report.cases):
        return VERDICT_ACCEPTED
    if any(case.verdict == VERDICT_WRONG_ANSWER for case in report.cases):
        return VERDICT_WRONG_ANSWER
    return report.cases[0].verdict


_NOISE = re.compile(
    r"^(?:Traceback \(most recent call last\)|\s*File \"|\s{4})", re.MULTILINE
)


def _clean_runtime_error(stderr: str, signal_number: int | None) -> str:
    if signal_number:
        names = {6: "SIGABRT", 9: "SIGKILL", 11: "SIGSEGV", 8: "SIGFPE"}
        return f"RuntimeError: the program was terminated by {names.get(signal_number, signal_number)}."
    text = (stderr or "").strip()
    if not text:
        return "RuntimeError: the program exited with a non-zero status and printed nothing."
    return format_output(text, 2000)


def _clean_compile_error(error: str, output: str) -> str:
    text = (output or "").strip() or (error or "").strip()
    return format_output(text, 2000) if text else "Compilation failed."


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def record_submission(*, user, problem, language, source_code, mode, report, custom=False):
    """Store a Submission (and its per-case rows) and update user progress."""
    from apps.progress.models import ProblemProgress
    from apps.submissions.models import RunMode, Submission, SubmissionTestResult, Verdict

    from .complexity import estimate_complexity

    verdict_map = {
        VERDICT_ACCEPTED: Verdict.ACCEPTED,
        VERDICT_WRONG_ANSWER: Verdict.WRONG_ANSWER,
        VERDICT_COMPILE_ERROR: Verdict.COMPILATION_ERROR,
        VERDICT_RUNTIME_ERROR: Verdict.RUNTIME_ERROR,
        VERDICT_TLE: Verdict.TIME_LIMIT_EXCEEDED,
        VERDICT_MLE: Verdict.MEMORY_LIMIT_EXCEEDED,
        VERDICT_EMPTY: Verdict.EMPTY_SUBMISSION,
        VERDICT_INTERNAL: Verdict.INTERNAL_ERROR,
    }

    estimate = estimate_complexity(source_code, language=language) if report.verdict != VERDICT_COMPILE_ERROR else None

    submission = Submission.objects.create(
        user=user,
        problem=problem,
        language=language,
        source_code=source_code,
        mode=RunMode.RUN if mode == "run" else RunMode.SUBMIT,
        verdict=verdict_map.get(report.verdict, Verdict.INTERNAL_ERROR),
        test_cases_passed=report.passed,
        total_test_cases=report.total,
        execution_time=report.total_time,
        max_execution_time=report.max_case_time,
        memory_used=report.max_memory,
        error_message=report.error_message,
        compile_output=report.compile_output,
        stdout=report.stdout,
        stderr=report.stderr,
        estimated_time_complexity=(estimate.time if estimate else ""),
        estimated_space_complexity=(estimate.space if estimate else ""),
        complexity_confidence=(estimate.confidence if estimate else ""),
        complexity_notes=("\n".join(estimate.notes) if estimate else ""),
    )

    for index, case in enumerate(report.cases):
        SubmissionTestResult.objects.create(
            submission=submission,
            test_case=case.test_case,
            order=index,
            label=case.label,
            input_data=format_output(case.input_data, 2000),
            expected_output=format_output(case.expected_output, 2000),
            actual_output=format_output(case.actual_output, 2000),
            verdict=verdict_map.get(case.verdict, Verdict.INTERNAL_ERROR),
            execution_time=case.execution_time,
            memory_used=case.memory_used,
            error=format_output(case.error, 2000),
            is_sample=case.is_sample,
            is_custom=case.is_custom,
        )

    if not custom:
        progress, _ = ProblemProgress.objects.get_or_create(user=user, problem=problem)
        progress.record_attempt(
            language=language,
            accepted=report.accepted,
            submission=submission,
        )
    return submission
