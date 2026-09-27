"""Home page: what to work on next."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.execution.models import Language
from apps.problems.models import Difficulty, Problem, UserPreference
from apps.progress.models import ProblemProgress, ProgressStatus
from apps.sheets.models import Sheet
from apps.submissions.models import Submission


@login_required
def index(request):
    """Landing page for a signed-in user."""
    preference = UserPreference.for_user(request.user)
    languages = Language.objects.enabled()

    recently_active = list(
        ProblemProgress.objects.filter(user=request.user)
        .exclude(status=ProgressStatus.NOT_STARTED)
        .select_related("problem", "last_language")
        .order_by("-updated_at")[:6]
    )
    in_progress = [row for row in recently_active if not row.is_solved][:3]

    solved_ids = set(
        ProblemProgress.objects.filter(
            user=request.user, status=ProgressStatus.SOLVED
        ).values_list("problem_id", flat=True)
    )

    resume = None
    if in_progress:
        row = in_progress[0]
        resume = {
            "progress": row,
            "language": row.last_language or preference.default_language,
            "url": row.problem.get_absolute_url(),
        }

    sheets = list(
        Sheet.objects.filter(is_active=True).with_sections().order_by("order", "name")[:4]
    )
    sheet_cards = []
    for sheet in sheets:
        ids = sheet.problem_ids
        solved = len(ids & solved_ids)
        sheet_cards.append(
            {
                "sheet": sheet,
                "sections": sheet.section_count,
                "problems": len(ids),
                "solved": solved,
                "total": len(ids),
                "percent": round(100.0 * solved / len(ids), 1) if ids else 0.0,
            }
        )

    total = Problem.objects.active().count()
    solved_total = len(solved_ids)
    submissions = Submission.objects.for_user(request.user)
    recent_submissions = submissions.select_related("problem", "language")[:5]

    return render(
        request,
        "dashboard/index.html",
        {
            "stats": {
                "problems": total,
                "solved": solved_total,
                "percent": round(100.0 * solved_total / total, 1) if total else 0.0,
                "attempts": submissions.count(),
                "languages": languages.count(),
            },
            "resume": resume,
            "recent_submissions": recent_submissions,
            "sheet_cards": sheet_cards,
            "languages": languages,
            "difficulty_counts": {
                Difficulty.EASY: Problem.objects.active()
                .filter(difficulty=Difficulty.EASY)
                .count(),
                Difficulty.MEDIUM: Problem.objects.active()
                .filter(difficulty=Difficulty.MEDIUM)
                .count(),
                Difficulty.HARD: Problem.objects.active()
                .filter(difficulty=Difficulty.HARD)
                .count(),
            },
        },
    )
