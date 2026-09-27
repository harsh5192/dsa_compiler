"""Per-user solving progress."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    ATTEMPTED = "attempted", "Attempted"
    SOLVED = "solved", "Solved"


class ProblemProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problem_progress"
    )
    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.CASCADE, related_name="progress_records"
    )
    status = models.CharField(
        max_length=15, choices=ProgressStatus.choices, default=ProgressStatus.NOT_STARTED
    )
    accepted = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)
    first_attempted_at = models.DateTimeField(null=True, blank=True)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_language = models.ForeignKey(
        "execution.Language", null=True, blank=True, on_delete=models.SET_NULL
    )
    last_submission = models.ForeignKey(
        "submissions.Submission",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "problem")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["-completed_at"]),
        ]

    def __str__(self):
        return f"{self.user} / {self.problem} = {self.get_status_display()}"

    @property
    def is_solved(self):
        return self.status == ProgressStatus.SOLVED

    def record_attempt(self, language=None, accepted=False, submission=None):
        """Update counters after a run/submit. Returns self."""
        now = timezone.now()
        if self.first_attempted_at is None:
            self.first_attempted_at = now
        self.last_attempted_at = now
        self.attempt_count += 1
        if language is not None:
            self.last_language = language
        if submission is not None:
            self.last_submission = submission
        if accepted:
            self.accepted = True
            if self.status != ProgressStatus.SOLVED:
                self.completed_at = now
            self.status = ProgressStatus.SOLVED
        elif self.status == ProgressStatus.NOT_STARTED:
            self.status = ProgressStatus.ATTEMPTED
        self.save(
            update_fields=[
                "first_attempted_at",
                "last_attempted_at",
                "attempt_count",
                "last_language",
                "last_submission",
                "accepted",
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        return self
