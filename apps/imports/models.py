"""Import job bookkeeping so imports are auditable and re-runnable."""

from django.conf import settings
from django.db import models


class ImportFormat(models.TextChoices):
    JSON = "json", "JSON"
    CSV = "csv", "CSV"
    LEETCODE = "leetcode", "LeetCode JSON"
    BACKUP = "backup", "Platform backup"


class ImportStatus(models.TextChoices):
    VALIDATED = "validated", "Validated"
    IMPORTED = "imported", "Imported"
    FAILED = "failed", "Failed"


class ImportJob(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_jobs",
    )
    source_file = models.CharField(max_length=300, blank=True)
    import_format = models.CharField(
        max_length=20, choices=ImportFormat.choices, default=ImportFormat.JSON
    )
    sheet = models.ForeignKey(
        "sheets.Sheet", null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(
        max_length=12, choices=ImportStatus.choices, default=ImportStatus.VALIDATED
    )
    dry_run = models.BooleanField(default=False)
    update_existing = models.BooleanField(default=True)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    test_case_count = models.PositiveIntegerField(default=0)
    section_count = models.PositiveIntegerField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_import_format_display()} import: {self.source_file} ({self.status})"
