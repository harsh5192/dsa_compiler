"""Sheet browser: the curated problem lists the platform ships with."""

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from apps.progress.models import ProblemProgress, ProgressStatus
from apps.sheets.models import Sheet, SheetProblem


@login_required
def sheet_list(request):
    sheets = list(
        Sheet.objects.filter(is_active=True).with_sections().order_by("order", "name")
    )
    solved_ids = set(
        ProblemProgress.objects.filter(
            user=request.user, status=ProgressStatus.SOLVED
        ).values_list("problem_id", flat=True)
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

    return render(
        request,
        "sheets/sheet_list.html",
        {"sheets": sheets, "sheet_cards": sheet_cards},
    )


@login_required
def sheet_detail(request, slug):
    sheet = get_object_or_404(
        Sheet.objects.filter(is_active=True).prefetch_related("sections"), slug=slug
    )
    sections = (
        sheet.sections.prefetch_related(
            Prefetch(
                "problems",
                queryset=SheetProblem.objects.filter(is_removed=False)
                .select_related("problem", "problem__primary_domain")
                .prefetch_related("problem__domains", "problem__tags"),
            )
        )
        .order_by("order", "id")
    )

    problem_ids = [
        entry.problem_id for section in sections for entry in section.problems.all()
    ]
    status_by_problem = {
        row["problem_id"]: row["status"]
        for row in ProblemProgress.objects.filter(
            user=request.user, problem_id__in=problem_ids
        ).values("problem_id", "status")
    }
    for section in sections:
        for entry in section.problems.all():
            entry.user_status = status_by_problem.get(entry.problem_id, "")

    done = sum(1 for status in status_by_problem.values() if status == "solved")
    total = len(problem_ids)

    return render(
        request,
        "sheets/sheet_detail.html",
        {
            "sheet": sheet,
            "sections": sections,
            "solved_count": done,
            "total_count": total,
            "percent": round(100.0 * done / total, 1) if total else 0.0,
        },
    )
