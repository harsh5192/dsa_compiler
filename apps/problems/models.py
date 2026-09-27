"""Problem, Domain, Tag, TestCase, StarterCode, SavedCode and user preferences."""

import json

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.execution.models import Language


class Difficulty(models.TextChoices):
    EASY = "Easy", "Easy"
    MEDIUM = "Medium", "Medium"
    HARD = "Hard", "Hard"

    @classmethod
    def rank(cls, value):
        return {"Easy": 0, "Medium": 1, "Hard": 2}.get(value, 99)


class ExecutionMode(models.TextChoices):
    FUNCTION = "function", "Function signature (harness calls your solution)"
    STDIN = "stdin", "Read from stdin, write to stdout"


COMPARISON_EXACT = "exact"
COMPARISON_UNORDERED = "unordered"
COMPARISON_MODES = (
    (COMPARISON_EXACT, "Exact (order matters)"),
    (COMPARISON_UNORDERED, "Unordered (group/order does not matter)"),
)


class Domain(models.Model):
    """A broad subject area, e.g. Array, Tree, Graph."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    order = models.PositiveIntegerField(default=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "domains"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """A technique or pattern, e.g. Two Pointer, BFS, Dynamic Programming."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "tags"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProblemQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related("primary_domain").prefetch_related(
            "domains", "tags", "starter_codes__language", "test_cases"
        )

    def active(self):
        return self.filter(is_active=True)

    def search(self, term):
        if not term:
            return self
        term = term.strip()
        from django.db.models import Q

        return self.filter(
            Q(title__icontains=term)
            | Q(slug__icontains=term)
            | Q(external_id__iexact=term)
            | Q(domains__name__icontains=term)
            | Q(tags__name__icontains=term)
            | Q(sheet_problems__section__sheet__name__icontains=term)
        ).distinct()


class Problem(models.Model):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True)
    description = models.TextField(
        blank=True, help_text="Supports basic HTML. Markdown is not rendered."
    )
    difficulty = models.CharField(
        max_length=10, choices=Difficulty.choices, default=Difficulty.EASY
    )
    # Convenience single domain for list display; the M2M below is authoritative.
    primary_domain = models.ForeignKey(
        Domain, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    domains = models.ManyToManyField(Domain, blank=True, related_name="problems")
    tags = models.ManyToManyField(Tag, blank=True, related_name="problems")

    constraints = models.TextField(blank=True, help_text="One constraint per line.")
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    examples = models.TextField(blank=True, help_text="Markdown/plain examples.")
    hints = models.TextField(blank=True, help_text="One hint per line.")
    explanation = models.TextField(blank=True)

    # --- execution contract -------------------------------------------------
    execution_mode = models.CharField(
        max_length=12,
        choices=ExecutionMode.choices,
        default=ExecutionMode.FUNCTION,
        help_text=(
            "'function': test case input is a JSON array of arguments and the "
            "harness calls the solution function. 'stdin': the raw text is "
            "piped to stdin and stdout is compared."
        ),
    )
    function_name = models.CharField(max_length=80, blank=True, default="solution")
    param_spec = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Ordered parameter type specs for compiled languages, e.g. "
            '["int[]", "int"]. Types: int, long, double, bool, string, '
            "int[], long[], double[], string[], int[][], ListNode, TreeNode."
        ),
    )
    return_spec = models.CharField(
        max_length=40,
        blank=True,
        help_text="Return type spec, e.g. int, int[], string, ListNode, void.",
    )
    time_limit = models.FloatField(null=True, blank=True)
    memory_limit_mb = models.PositiveIntegerField(null=True, blank=True)

    # --- expected (reference) complexity ------------------------------------
    expected_time_complexity = models.CharField(max_length=40, blank=True)
    expected_space_complexity = models.CharField(max_length=40, blank=True)
    solution_notes = models.TextField(blank=True)

    # --- provenance ---------------------------------------------------------
    source = models.CharField(max_length=120, blank=True, default="Custom")
    source_url = models.URLField(blank=True)
    external_id = models.CharField(
        max_length=40, blank=True, db_index=True, help_text="e.g. LeetCode id '1'."
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProblemQuerySet.as_manager()

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["difficulty"]),
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "problem"
            slug, i = base, 2
            while Problem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        if isinstance(self.param_spec, str):
            try:
                self.param_spec = json.loads(self.param_spec or "[]")
            except json.JSONDecodeError:
                self.param_spec = []
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("problems:detail", kwargs={"slug": self.slug})

    # -- helpers ------------------------------------------------------------
    @property
    def domain_names(self):
        return [d.name for d in self.domains.all()]

    @property
    def tag_names(self):
        return [t.name for t in self.tags.all()]

    @property
    def display_domain(self):
        if self.primary_domain_id:
            return self.primary_domain.name
        domains = list(self.domains.all())
        return domains[0].name if domains else "General"

    @property
    def sample_test_cases(self):
        return [tc for tc in self.test_cases.all() if tc.is_sample and not tc.is_hidden]

    @property
    def all_test_cases(self):
        return list(self.test_cases.all())

    @property
    def sheet_names(self):
        names = []
        for sp in self.sheet_problems.select_related("section__sheet").all():
            sheet = sp.section.sheet
            if sheet.name not in names:
                names.append(sheet.name)
        return names

    def starter_code_for(self, language):
        if not language:
            return None
        code = self.starter_codes.filter(language=language).first()
        if code:
            return code
        # Fall back to the problem's default template for that language family.
        if getattr(language, "default_starter_code", ""):
            return DefaultStarterCode(
                language=language, starter_code=language.default_starter_code
            )
        return None

    @property
    def test_case_count(self):
        return self.test_cases.count()


class DefaultStarterCode:
    """Lightweight stand-in returned by Problem.starter_code_for fallbacks."""

    def __init__(self, language, starter_code):
        self.language = language
        self.starter_code = starter_code


class TestCase(models.Model):
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="test_cases"
    )
    name = models.CharField(max_length=120, blank=True)
    input_data = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    is_sample = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    # ``exact`` compares the JSON output structurally, ``unordered`` also sorts
    # nested lists first (useful for "group the words" style problems where any
    # group ordering is acceptable).
    comparison = models.CharField(
        max_length=16,
        choices=COMPARISON_MODES,
        default=COMPARISON_EXACT,
    )
    # Problems with more than one correct answer (backtracking, constructive
    # tasks) name a semantic checker instead of relying on a stored answer.
    checker = models.CharField(max_length=32, blank=True, default="")
    # Optional per-test-case override, mostly useful for imported data.
    expected_time_ms = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        label = self.name or f"Test case {self.order + 1}"
        return f"{self.problem.title} - {label}"

    @property
    def label(self):
        return self.name or f"Test case {self.order + 1}"


class ProblemStarterCode(models.Model):
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="starter_codes"
    )
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name="starter_codes"
    )
    starter_code = models.TextField()
    solution_reference = models.TextField(
        blank=True, help_text="Optional reference solution used for self-checks."
    )

    class Meta:
        unique_together = ("problem", "language")
        ordering = ["language__order", "language__name"]

    def __str__(self):
        return f"{self.problem.title} ({self.language.name})"


class SavedCode(models.Model):
    """Latest code for a (user, problem, language) triple - survives revisits."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_code"
    )
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="saved_codes"
    )
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name="saved_codes"
    )
    code = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "problem", "language")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} / {self.problem} / {self.language}"


class UserPreference(models.Model):
    """Per-user UI + execution settings, edited on the Settings page."""

    THEME_CHOICES = [("light", "Light"), ("dark", "Dark"), ("system", "System")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preference"
    )
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="system")
    default_language = models.ForeignKey(
        Language,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="preferred_by",
    )
    editor = models.CharField(max_length=20, default="monaco")
    editor_theme = models.CharField(max_length=30, default="vs-dark")
    editor_font_size = models.PositiveSmallIntegerField(default=14)
    show_editor_intro = models.BooleanField(
        default=True, help_text="Show the editor guide panel on the problem page."
    )
    autosave = models.BooleanField(default=True)
    autosave_delay_ms = models.PositiveIntegerField(default=1200)
    execution_timeout = models.FloatField(
        default=5.0, help_text="Default per-test-case time limit in seconds."
    )
    keyboard_shortcuts = models.BooleanField(default=True)
    run_shortcut = models.CharField(max_length=20, default="Ctrl+Enter")
    submit_shortcut = models.CharField(max_length=20, default="Ctrl+Shift+Enter")
    save_shortcut = models.CharField(max_length=20, default="Ctrl+S")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user}"

    @classmethod
    def for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj
