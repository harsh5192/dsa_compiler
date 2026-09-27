"""Language registry model.

Languages are data, not code: a new language is a database row plus (optionally)
a runner in :mod:`apps.execution.runners`.  Adding one therefore does not
require touching the rest of the application.
"""

from django.db import models
from django.utils.text import slugify


class LanguageQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(enabled=True)


class Language(models.Model):
    """A programming language the platform can compile and run."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    file_extension = models.CharField(max_length=12, default=".txt")
    enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=100)

    # --- how to build and run it -------------------------------------------
    # Key into apps.execution.runners.RUNNERS.  When empty the platform falls
    # back to a generic "script" runner driven by the command templates.
    runner = models.CharField(max_length=40, default="script")

    # Template commands.  Placeholders: {file} (absolute path to the source
    # file), {out} (binary/class file path), {file_name} (basename), {dir}.
    compile_command = models.TextField(
        blank=True,
        help_text="Leave empty for interpreted languages. e.g. g++ {file} -O2 -o {out}",
    )
    execution_command = models.TextField(
        blank=True,
        help_text="e.g. {python} {file_name}",
    )
    # Extra environment variables added when running (already split key/value).
    run_env = models.JSONField(default=dict, blank=True)

    # --- limits -------------------------------------------------------------
    time_limit = models.FloatField(
        default=5.0, help_text="Wall clock seconds per test case."
    )
    memory_limit_mb = models.PositiveIntegerField(
        default=512, help_text="Address space / heap cap in megabytes."
    )
    # Some runtimes (JVM) reserve huge virtual address spaces and must not get
    # RLIMIT_AS; they rely on their own heap flags plus RSS measurement.
    enforce_address_space_limit = models.BooleanField(default=True)
    compile_timeout = models.FloatField(default=30.0)

    # --- editor -------------------------------------------------------------
    monaco_language = models.CharField(
        max_length=30, default="plaintext", help_text="Monaco language id."
    )
    editor_mode = models.CharField(
        max_length=30, blank=True, help_text="Monaco editor mode override."
    )
    comment_prefix = models.CharField(max_length=4, default="#")

    # --- optional strong isolation -----------------------------------------
    docker_image = models.CharField(
        max_length=120, blank=True, help_text="Optional sandbox image."
    )

    notes = models.TextField(blank=True)

    objects = LanguageQuerySet.as_manager()

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_compiled(self):
        return bool(self.compile_command.strip())
