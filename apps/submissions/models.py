"""Submission records and per-test-case results."""

from django.conf import settings
from django.db import models
from django.urls import reverse


class Verdict(models.TextChoices):
    ACCEPTED = "accepted", "Accepted"
    WRONG_ANSWER = "wrong_answer", "Wrong Answer"
    COMPILATION_ERROR = "compilation_error", "Compilation Error"
    RUNTIME_ERROR = "runtime_error", "Runtime Error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded", "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded", "Memory Limit Exceeded"
    EMPTY_SUBMISSION = "empty_submission", "Empty Submission"
    INTERNAL_ERROR = "internal_error", "Internal Error"


#: Verdicts that count as a successful solve.
ACCEPTED_VERDICTS = {Verdict.ACCEPTED}


class RunMode(models.TextChoices):
    RUN = "run", "Run (sample/custom cases)"
    SUBMIT = "submit", "Submit (all cases)"


class SubmissionQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def accepted(self):
        return self.filter(verdict=Verdict.ACCEPTED)


class Submission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.CASCADE, related_name="submissions"
    )
    language = models.ForeignKey(
        "execution.Language", on_delete=models.SET_NULL, null=True, blank=True
    )
    source_code = models.TextField(blank=True)
    mode = models.CharField(max_length=8, choices=RunMode.choices, default=RunMode.SUBMIT)

    verdict = models.CharField(
        max_length=32, choices=Verdict.choices, default=Verdict.INTERNAL_ERROR
    )
    test_cases_passed = models.PositiveIntegerField(default=0)
    total_test_cases = models.PositiveIntegerField(default=0)
    execution_time = models.FloatField(default=0.0, help_text="Total seconds.")
    max_execution_time = models.FloatField(
        default=0.0, help_text="Slowest single test case, seconds."
    )
    memory_used = models.BigIntegerField(
        default=0, help_text="Peak RSS in bytes, best effort."
    )
    error_message = models.TextField(blank=True)
    compile_output = models.TextField(blank=True)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)

    # Heuristic, explicitly-labelled complexity estimate.
    estimated_time_complexity = models.CharField(max_length=40, blank=True)
    estimated_space_complexity = models.CharField(max_length=40, blank=True)
    complexity_confidence = models.CharField(max_length=10, blank=True)
    complexity_notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = SubmissionQuerySet.as_manager()

    class Meta:
        ordering = ["-submitted_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-submitted_at"]),
            models.Index(fields=["problem", "-submitted_at"]),
        ]

    def __str__(self):
        return f"{self.problem} - {self.get_verdict_display()} ({self.submitted_at:%Y-%m-%d %H:%M})"

    @property
    def is_accepted(self):
        return self.verdict == Verdict.ACCEPTED

    @property
    def passed_all(self):
        return self.total_test_cases > 0 and self.test_cases_passed == self.total_test_cases

    def get_absolute_url(self):
        return reverse("submissions:detail", kwargs={"pk": self.pk})

    @property
    def execution_time_display(self):
        if self.execution_time and self.execution_time < 1:
            return f"{self.execution_time * 1000:.0f} ms"
        return f"{self.execution_time:.3f} s"

    @property
    def memory_display(self):
        if not self.memory_used:
            return "-"
        mb = self.memory_used / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GB"
        return f"{mb:.1f} MB"


class SubmissionTestResult(models.Model):
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="test_results"
    )
    test_case = models.ForeignKey(
        "problems.TestCase",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="results",
    )
    order = models.PositiveIntegerField(default=0)
    label = models.CharField(max_length=120, blank=True)
    input_data = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    actual_output = models.TextField(blank=True)
    verdict = models.CharField(max_length=32, choices=Verdict.choices, blank=True)
    execution_time = models.FloatField(default=0.0)
    memory_used = models.BigIntegerField(default=0)
    error = models.TextField(blank=True)
    is_sample = models.BooleanField(default=False)
    is_custom = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.submission_id} case {self.order + 1}: {self.verdict}"

    @property
    def passed(self):
        return self.verdict == Verdict.ACCEPTED
