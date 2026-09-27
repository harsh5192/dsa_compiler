"""DSA sheets: Sheet -> SheetSection -> SheetProblem -> Problem."""

from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class SheetQuerySet(models.QuerySet):
    def with_sections(self):
        """Prefetch sections *and* their problem slots so the count properties
        below answer from memory instead of issuing a query per sheet."""
        return self.prefetch_related("sections__problems")


class Sheet(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=150, blank=True, default="Custom")
    source_url = models.URLField(blank=True)
    version = models.CharField(max_length=40, blank=True, default="1.0")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SheetQuerySet.as_manager()

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "sheets"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:180] or "sheet"
            slug, i = base, 2
            while Sheet.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("sheets:detail", kwargs={"slug": self.slug})

    def _prefetched(self, name):
        return (getattr(self, "_prefetched_objects_cache", None) or {}).get(name)

    @property
    def problem_count(self):
        """Distinct problems in active (non-removed) slots."""
        sections = self._prefetched("sections")
        if sections is not None:
            return sum(
                1
                for section in sections
                for entry in (getattr(section, "_prefetched_objects_cache", None) or {}).get(
                    "problems", []
                )
                if not entry.is_removed
            )
        return self.sections.aggregate(
            n=models.Count("problems__problem", filter=models.Q(problems__is_removed=False), distinct=True)
        )["n"]

    @property
    def section_count(self):
        sections = self._prefetched("sections")
        if sections is not None:
            return len(sections)
        return self.sections.count()

    @property
    def problem_ids(self):
        """Problem ids in active slots, in sheet order (prefetch friendly)."""
        sections = self._prefetched("sections")
        if sections is None:
            return set(
                self.sections.filter(problems__is_removed=False).values_list(
                    "problems__problem_id", flat=True
                )
            )
        return {
            entry.problem_id
            for section in sections
            for entry in (getattr(section, "_prefetched_objects_cache", None) or {}).get(
                "problems", []
            )
            if not entry.is_removed
        }


class SheetSection(models.Model):
    sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("sheet", "slug")

    def __str__(self):
        return f"{self.sheet.name} :: {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200]
        super().save(*args, **kwargs)

    @property
    def active_problems(self):
        return self.problems.filter(is_removed=False).select_related("problem")


class SheetProblem(models.Model):
    section = models.ForeignKey(
        SheetSection, on_delete=models.CASCADE, related_name="problems"
    )
    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.CASCADE, related_name="sheet_problems"
    )
    order = models.PositiveIntegerField(default=0)
    is_removed = models.BooleanField(
        default=False, help_text="Keeps a slot without deleting the problem."
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("section", "problem")

    def __str__(self):
        return f"{self.problem.title} @ {self.section.name}"
