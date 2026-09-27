"""JSON endpoints the browser editor talks to.

Three actions, all POST-only and CSRF protected:

``run``      compile and execute the sample (or supplied custom) cases
``submit``   execute every case and record a Submission plus progress
``save``     store the editor contents for the next visit

Each returns the same envelope so the front end has one code path::

    {"ok": true, "report": {...}, "complexity": {...}}
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.execution import service
from apps.execution.complexity import compare_to_expected, estimate_complexity
from apps.execution.models import Language
from apps.execution.sandbox import cleanup_workdir, make_workdir
from apps.execution.starter import generate as generate_starter
from apps.problems.models import Problem, SavedCode
from apps.progress.models import ProblemProgress
from apps.submissions.models import RunMode, Submission, SubmissionTestResult, Verdict

logger = logging.getLogger(__name__)

MAX_CODE_BYTES = 256 * 1024
MAX_CUSTOM_CASES = 20

#: Pseudo-verdict for a custom case with no expected output: the user is only
#: asking "what does my code print?", so pass/fail would be a lie.
VERDICT_CUSTOM_OUTPUT = "custom"


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


def _payload(request) -> dict:
    """Accept either a JSON body or a normal form post."""
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return request.POST.dict()


def _looks_like_case_list(value: list) -> bool:
    """Is this JSON array a *list of cases* rather than one argument list?

    ``[[2,7],[9]]`` and ``[{"input": "..."}, ...]`` are several cases; a flat
    ``[2,7,9]`` is one case whose arguments are 2, 7 and 9.
    """
    if not value:
        return False
    if all(isinstance(entry, dict) and "input" in entry for entry in value):
        return True
    if all(isinstance(entry, list) for entry in value):
        return True
    return False


def _parse_custom_cases(raw) -> list:
    """Build transient test cases from the editor's custom input box.

    They are not stored: they exist only for this one run, which is exactly what
    "try my own input" should mean.

    Accepted shapes::

        [[2, 7, 11, 15], 9]            one case, two arguments
        [[[2, 7], 9], [[3, 3], 6]]      two cases
        [{"input": "[2,7],9",
          "expected_output": "[0,1]"}]  one case with an expected answer
        hello                           one raw stdin case
    """
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            # Allow a single non-JSON payload, e.g. `hello`.
            return [_case(text, "", 1)]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    if not _looks_like_case_list(raw):
        raw = [raw]

    cases = []
    for entry in raw[:MAX_CUSTOM_CASES]:
        if isinstance(entry, dict) and "input" in entry:
            input_data = str(entry.get("input", "")).strip()
            expected = entry.get("expected_output", entry.get("expected", ""))
        else:
            input_data = json.dumps(entry)
            expected = ""
        if not input_data:
            continue
        cases.append(_case(input_data, expected, len(cases) + 1))
    return cases


def _case(input_data: str, expected, index: int) -> dict:
    return {
        "label": f"Custom case {index}",
        "input_data": input_data,
        "expected_output": "" if expected is None else str(expected),
        "is_sample": False,
        "is_hidden": False,
        "is_custom": True,
        "comparison": "exact",
        "checker": "",
    }


def _relabel_informational_cases(report, custom_cases) -> None:
    """Mark custom cases that had no expected answer as informational.

    The judge still records a verdict for them (nothing to compare against
    means "wrong answer"), which would be misleading in the Run panel, so the
    run view rewrites those verdicts to :data:`VERDICT_CUSTOM_OUTPUT`.
    """
    unlabelled = {
        case["label"] for case in custom_cases if not case["expected_output"].strip()
    }
    if not unlabelled:
        return
    for result in report.cases:
        if result.is_custom and result.label in unlabelled:
            result.verdict = VERDICT_CUSTOM_OUTPUT


def _estimate(problem, language, source: str) -> dict:
    estimate = estimate_complexity(source, language)
    payload = estimate.to_dict()
    payload["notes"] = payload["notes"] + compare_to_expected(
        estimate,
        problem.expected_time_complexity,
        problem.expected_space_complexity,
    )
    payload["expected"] = {
        "time": problem.expected_time_complexity,
        "space": problem.expected_space_complexity,
    }
    return payload


def _context(request, data):
    problem = Problem.objects.filter(slug=str(data.get("problem", ""))).first()
    if problem is None:
        return None, None, "Unknown problem."
    language = next(
        (
            l
            for l in Language.objects.enabled()
            if l.slug == str(data.get("language", ""))
        ),
        None,
    )
    if language is None:
        return None, None, "Choose a language first."
    return problem, language, ""


def health(request):
    """Unauthenticated liveness probe: is the app and its database answering?"""
    from django.db import connection

    database = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - only on a broken database
        database = f"error: {exc}"

    return JsonResponse(
        {
            "ok": database == "ok",
            "database": database,
            "backend": settings.DSA_EXECUTION_BACKEND,
            "languages": list(Language.objects.enabled().values_list("slug", flat=True)),
        },
        status=200 if database == "ok" else 503,
    )


@login_required
@require_POST
def run(request):
    """Execute against sample (or custom) cases. Nothing is recorded."""
    data = _payload(request)
    problem, language, problem_error = _context(request, data)
    if problem is None:
        return _error(problem_error)

    source = str(data.get("code", ""))
    if len(source.encode("utf-8", "ignore")) > MAX_CODE_BYTES:
        return _error("That is a lot of code; please keep it under 256 KB.", 413)

    custom_cases = _parse_custom_cases(data.get("custom_cases"))
    workdir = make_workdir(prefix=f"run-p{problem.pk}")
    try:
        report = service.execute(
            problem=problem,
            language=language,
            source_code=source,
            mode="run",
            custom_cases=custom_cases or None,
            workdir=workdir,
        )
    except service.ExecutionUnavailable as exc:
        return _error(str(exc), 503)
    except Exception:  # pragma: no cover - defensive
        logger.exception("run failed for problem %s", problem.slug)
        return _error("The runner failed unexpectedly. Check the server log.", 500)
    finally:
        _cleanup(workdir)

    _relabel_informational_cases(report, custom_cases)

    if data.get("save", True) and source.strip():
        SavedCode.objects.update_or_create(
            user=request.user,
            problem=problem,
            language=language,
            defaults={"code": source},
        )

    return JsonResponse(
        {
            "ok": True,
            "mode": "run",
            "report": report.to_dict(),
            "complexity": _estimate(problem, language, source),
            "custom_case_count": len(custom_cases),
        }
    )


@login_required
@require_POST
def submit(request):
    """Execute every case, record a Submission and update progress."""
    data = _payload(request)
    problem, language, problem_error = _context(request, data)
    if problem is None:
        return _error(problem_error)

    source = str(data.get("code", ""))
    if len(source.encode("utf-8", "ignore")) > MAX_CODE_BYTES:
        return _error("That is a lot of code; please keep it under 256 KB.", 413)

    workdir = make_workdir(prefix=f"sub-p{problem.pk}")
    try:
        report = service.execute(
            problem=problem,
            language=language,
            source_code=source,
            mode="submit",
            workdir=workdir,
        )
    except service.ExecutionUnavailable as exc:
        return _error(str(exc), 503)
    except Exception:  # pragma: no cover - defensive
        logger.exception("submit failed for problem %s", problem.slug)
        return _error("The runner failed unexpectedly. Check the server log.", 500)
    finally:
        _cleanup(workdir)

    complexity = _estimate(problem, language, source)
    verdict = report.verdict
    if verdict not in dict(Verdict.choices):
        verdict = Verdict.INTERNAL_ERROR

    submission = Submission.objects.create(
        user=request.user,
        problem=problem,
        language=language,
        source_code=source,
        mode=RunMode.SUBMIT,
        verdict=verdict,
        test_cases_passed=report.passed,
        total_test_cases=report.total,
        execution_time=report.total_time,
        max_execution_time=report.max_case_time,
        memory_used=report.max_memory,
        error_message=report.error_message,
        compile_output=report.compile_output,
        stdout=report.stdout,
        stderr=report.stderr,
        estimated_time_complexity=complexity["time"],
        estimated_space_complexity=complexity["space"],
        complexity_confidence=complexity["confidence"],
        complexity_notes="\n".join(complexity["notes"]),
    )
    SubmissionTestResult.objects.bulk_create(
        [
            SubmissionTestResult(
                submission=submission,
                test_case=case.test_case,
                order=index,
                label=case.label,
                input_data=case.input_data,
                expected_output=case.expected_output,
                actual_output=case.actual_output,
                verdict=case.verdict if case.verdict in dict(Verdict.choices) else Verdict.INTERNAL_ERROR,
                execution_time=case.execution_time,
                memory_used=case.memory_used,
                error=case.error,
                is_sample=case.is_sample,
                is_custom=case.is_custom,
            )
            for index, case in enumerate(report.cases)
        ]
    )

    progress, _ = ProblemProgress.objects.get_or_create(
        user=request.user, problem=problem
    )
    progress.record_attempt(
        language=language, accepted=report.accepted, submission=submission
    )
    if source.strip():
        SavedCode.objects.update_or_create(
            user=request.user,
            problem=problem,
            language=language,
            defaults={"code": source},
        )

    payload = {
        "ok": True,
        "mode": "submit",
        "report": report.to_dict(),
        "complexity": complexity,
        "submission_id": submission.pk,
        "submission_url": submission.get_absolute_url(),
        "progress": {
            "status": progress.status,
            "attempt_count": progress.attempt_count,
            "solved": progress.is_solved,
        },
    }
    return JsonResponse(payload)


@login_required
@require_POST
def save_code(request):
    """Autosave: keep the editor contents for the next visit."""
    data = _payload(request)
    problem, language, problem_error = _context(request, data)
    if problem is None:
        return _error(problem_error)
    code = str(data.get("code", ""))
    if len(code.encode("utf-8", "ignore")) > MAX_CODE_BYTES:
        return _error("That is a lot of code; please keep it under 256 KB.", 413)
    SavedCode.objects.update_or_create(
        user=request.user, problem=problem, language=language, defaults={"code": code}
    )
    return JsonResponse({"ok": True, "saved": len(code)})


@login_required
def starter(request, slug):
    """Starter code for a (problem, language) pair, for the 'reset' button."""
    problem = Problem.objects.filter(slug=slug).first()
    language = next(
        (l for l in Language.objects.enabled() if l.slug == request.GET.get("language")),
        None,
    )
    if problem is None or language is None:
        return _error("Unknown problem or language.", 404)
    stored = problem.starter_code_for(language)
    code = stored.starter_code if stored is not None else generate_starter(problem, language)
    return JsonResponse(
        {
            "ok": True,
            "language": language.slug,
            "monaco_language": language.monaco_language,
            "code": code,
        }
    )


def _cleanup(workdir) -> None:
    """Remove a workdir this view created; ``execute`` only cleans its own."""
    if not workdir:
        return
    try:
        cleanup_workdir(workdir)
    except Exception:  # pragma: no cover - best effort
        logger.debug("could not remove workdir %s", workdir)
