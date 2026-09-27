"""Per-user solving progress."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from apps.problems.models import Difficulty, Problem
from apps.progress.models import ProblemProgress, ProgressStatus


@login_required
def index(request):
    rows = (
        ProblemProgress.objects.filter(user=request.user)
        .select_related("problem", "problem__primary_domain", "last_language")
    )
    status = (request.GET.get("status") or "").strip()
    if status in dict(ProgressStatus.choices):
        rows = rows.filter(status=status)
    domain = (request.GET.get("domain") or "").strip()
    if domain:
        rows = rows.filter(problem__domains__slug=domain)

    solved = (
        ProblemProgress.objects.filter(user=request.user, status=ProgressStatus.SOLVED)
        .select_related("problem", "problem__primary_domain", "last_language")
        .order_by("-completed_at")[:20]
    )

    counts = (
        ProblemProgress.objects.filter(user=request.user)
        .values("status")
        .annotate(n=Count("id"))
    )
    by_status = {row["status"]: row["n"] for row in counts}

    total = Problem.objects.active().count()
    solved_total = by_status.get(ProgressStatus.SOLVED, 0)

    by_difficulty = {
        level: ProblemProgress.objects.filter(
            user=request.user, status=ProgressStatus.SOLVED, problem__difficulty=level
        ).count()
        for level in (Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD)
    }
    by_domain = list(
        ProblemProgress.objects.filter(user=request.user, status=ProgressStatus.SOLVED)
        .values("problem__primary_domain__name")
        .annotate(n=Count("id"))
        .order_by("-n")[:8]
    )

    return render(
        request,
        "progress/index.html",
        {
            "rows": rows[:60],
            "solved": solved,
            "by_status": by_status,
            "by_difficulty": by_difficulty,
            "by_domain": by_domain,
            "status": status,
            "domain": domain,
            "statuses": ProgressStatus.choices,
            "total": total,
            "solved_total": solved_total,
            "percent": round(100.0 * solved_total / total, 1) if total else 0.0,
            "domains": (
                Problem.objects.active()
                .values("domains__slug", "domains__name")
                .exclude(domains__slug="")
                .order_by("domains__name")
                .distinct()
            ),
        },
    )
