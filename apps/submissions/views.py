"""Submission history."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Submission

PAGE_SIZE = 25


@login_required
def submission_list(request):
    submissions = (
        Submission.objects.for_user(request.user)
        .select_related("problem", "language")
    )
    verdict = (request.GET.get("verdict") or "").strip()
    if verdict:
        submissions = submissions.filter(verdict=verdict)

    paginator = Paginator(submissions, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "submissions/submission_list.html",
        {
            "page": page,
            "submissions": page.object_list,
            "verdict": verdict,
            "verdicts": Submission._meta.get_field("verdict").choices,
            "total": submissions.count(),
        },
    )


@login_required
def submission_detail(request, pk):
    submission = get_object_or_404(
        Submission.objects.for_user(request.user).select_related(
            "problem", "language"
        ),
        pk=pk,
    )
    return render(
        request,
        "submissions/submission_detail.html",
        {"submission": submission, "results": submission.test_results.all()},
    )
