"""Problem list and the solve page (statement + editor + verdicts)."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.execution.models import Language
from apps.execution.starter import generate as generate_starter
from apps.progress.models import ProblemProgress, ProgressStatus
from apps.problems.models import Problem, UserPreference
from apps.sheets.models import Sheet
from apps.submissions.models import Submission

PAGE_SIZE = 24


@login_required
def problem_list(request):
    """Searchable, filterable catalogue of every active problem."""
    problems = Problem.objects.active().with_relations()

    query = (request.GET.get("q") or "").strip()
    if query:
        problems = problems.search(query)

    difficulty = (request.GET.get("difficulty") or "").strip()
    if difficulty in {"Easy", "Medium", "Hard"}:
        problems = problems.filter(difficulty=difficulty)

    domain = (request.GET.get("domain") or "").strip()
    if domain:
        problems = problems.filter(domains__slug=domain)

    sheet = (request.GET.get("sheet") or "").strip()
    if sheet:
        problems = problems.filter(
            sheet_problems__section__sheet__slug=sheet,
            sheet_problems__is_removed=False,
        )

    tag = (request.GET.get("tag") or "").strip()
    if tag:
        problems = problems.filter(tags__slug=tag)

    sort = (request.GET.get("sort") or "").strip()
    order_by = {
        "title": ["title"],
        "difficulty": ["difficulty", "title"],
        "updated": ["-updated_at"],
    }.get(sort, ["title"])
    problems = problems.distinct().order_by(*order_by)

    solved_ids = set(
        ProblemProgress.objects.filter(
            user=request.user, status=ProgressStatus.SOLVED
        ).values_list("problem_id", flat=True)
    )
    attempted_ids = set(
        ProblemProgress.objects.filter(
            user=request.user, status=ProgressStatus.ATTEMPTED
        ).values_list("problem_id", flat=True)
    )

    paginator = Paginator(problems, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    # Annotate the visible page only; a global count would defeat pagination.
    solved_in_page = solved_ids & {p.pk for p in page.object_list}
    for problem in page.object_list:
        problem.user_status = (
            "solved"
            if problem.pk in solved_in_page
            else "attempted"
            if problem.pk in attempted_ids
            else ""
        )

    return render(
        request,
        "problems/problem_list.html",
        {
            "page": page,
            "paginator": paginator,
            "problems": page.object_list,
            "query": query,
            "difficulty": difficulty,
            "domain": domain,
            "tag": tag,
            "sheet": sheet,
            "sort": sort,
            "domains": Problem.objects.active()
            .values("domains__slug", "domains__name")
            .exclude(domains__slug="")
            .order_by("domains__name")
            .distinct(),
            "sheets": Sheet.objects.filter(is_active=True),
            "solved_total": len(solved_ids),
            "total_active": Problem.objects.active().count(),
        },
    )


@login_required
def problem_detail(request, slug):
    """The solve page: statement on the left, editor and verdicts on the right."""
    problem = (
        Problem.objects.active()
        .with_relations()
        .filter(slug=slug)
        .first()
    )
    if problem is None:
        problem = get_object_or_404(Problem, slug=slug)

    languages = Language.objects.enabled()
    preference = UserPreference.for_user(request.user)
    requested = (request.GET.get("language") or "").strip()
    language = None
    if requested:
        language = next((l for l in languages if l.slug == requested), None)
    if language is None and preference is not None and preference.default_language_id:
        language = languages.filter(pk=preference.default_language_id).first()
    if language is None:
        saved_languages = list(
            problem.saved_codes.filter(user=request.user)
            .select_related("language")
            .order_by("-updated_at")
            .values_list("language", flat=True)
        )
        language = next((l for l in languages if l.slug in saved_languages), languages[0] if languages else None)

    # Starter code: stored per problem, else generated from the signature.
    starter = problem.starter_code_for(language) if language else None
    code = ""
    if language:
        saved = problem.saved_codes.filter(user=request.user, language=language).first()
        if saved and saved.code.strip():
            code = saved.code
        elif starter is not None:
            code = starter.starter_code
        else:
            code = generate_starter(problem, language)

    samples = [
        {
            "label": case.label,
            "input": case.input_data,
            "expected": case.expected_output,
            "explanation": case.explanation,
        }
        for case in problem.sample_test_cases
    ]

    progress = ProblemProgress.objects.filter(
        user=request.user, problem=problem
    ).first()
    history = (
        Submission.objects.for_user(request.user)
        .filter(problem=problem)
        .select_related("language")[:8]
    )
    total_cases = problem.test_cases.count()

    return render(
        request,
        "problems/problem_detail.html",
        {
            "problem": problem,
            "languages": languages,
            "language": language,
            "code": code,
            "samples": samples,
            "total_cases": total_cases,
            "progress": progress,
            "history": history,
            "sheets": problem.sheet_problems.select_related("section__sheet"),
            "editor": (preference.editor if preference else "monaco"),
            "editor_theme": (preference.editor_theme if preference else "vs-dark"),
            "editor_font_size": (preference.editor_font_size if preference else 14),
            "autosave": bool(preference.autosave) if preference else True,
            "autosave_delay_ms": (preference.autosave_delay_ms if preference else 1200),
            "show_intro": bool(preference.show_editor_intro) if preference else True,
            "run_shortcut": (preference.run_shortcut if preference else "Ctrl+Enter"),
            "submit_shortcut": (preference.submit_shortcut if preference else "Ctrl+Shift+Enter"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def toggle_sheet_problem(request, slug, entry_id):
    """Mark a sheet slot as removed/active again, keeping the problem itself."""
    problem = get_object_or_404(Problem, slug=slug)
    entry = get_object_or_404(
        problem.sheet_problems.select_related("section__sheet"), pk=entry_id
    )
    entry.is_removed = not entry.is_removed
    entry.save(update_fields=["is_removed"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"removed": entry.is_removed})
    return redirect(problem.get_absolute_url())
