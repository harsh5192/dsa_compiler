"""Shared importer machinery.

An importer is split in two halves:

``parse`` / ``normalize``
    Pure data work: turn a file's bytes into the canonical payload structure
    below, collecting warnings instead of touching the database.  This is what
    powers the "preview" step in the Import page.

``apply``
    The only part that writes.  It is shared by every format so duplicate
    detection, starter-code generation and test-case import behave identically
    no matter where the data came from.

Canonical payload::

    {
      "name": "My sheet",
      "description": "...",
      "source": "Custom",
      "sections": [
        {"name": "Arrays", "order": 1, "problems": [ <problem>, ... ]}
      ],
      "problems": [ <problem>, ...],          # problems without a section
    }

``<problem>`` is a dict as produced by :func:`normalize_problem`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from django.db import transaction
from django.utils.text import slugify

from apps.execution.starter import generate as generate_starter
from apps.execution.checkers import checker_names
from apps.execution.typespec import TypeSpec
from apps.execution.typespec import normalize as normalize_type
from apps.problems.models import (
    COMPARISON_EXACT,
    COMPARISON_UNORDERED,
    Difficulty,
    Domain,
    ExecutionMode,
    Problem,
    Tag,
    TestCase,
)

VALID_DIFFICULTIES = {c[0].lower(): c[0] for c in Difficulty.choices}
VALID_COMPARISON_MODES = {COMPARISON_EXACT, COMPARISON_UNORDERED}
VALID_CHECKERS = set(checker_names())
VALID_DIFFICULTY_ALIASES = {
    "e": "Easy",
    "s": "Easy",
    "m": "Medium",
    "h": "Hard",
    "beginner": "Easy",
    "basic": "Easy",
    "intermediate": "Medium",
    "advanced": "Hard",
}

MODE_ALIASES = {
    "function": ExecutionMode.FUNCTION,
    "signature": ExecutionMode.FUNCTION,
    "class": ExecutionMode.FUNCTION,
    "call": ExecutionMode.FUNCTION,
    "stdin": ExecutionMode.STDIN,
    "stdio": ExecutionMode.STDIN,
    "console": ExecutionMode.STDIN,
    "io": ExecutionMode.STDIN,
}


class ImportValidationError(Exception):
    """Raised when a file cannot be understood at all."""


@dataclass
class ProblemPreview:
    title: str
    slug: str
    state: str  # "new" | "existing"
    domains: list = field(default_factory=list)
    difficulty: str = ""
    test_cases: int = 0
    reason: str = ""


@dataclass
class ImportPreview:
    name: str = ""
    description: str = ""
    source: str = ""
    version: str = ""
    sections: list = field(default_factory=list)
    problems: list = field(default_factory=list)
    test_case_count: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    payload: dict = field(default_factory=dict)
    valid: bool = True

    @property
    def new_count(self) -> int:
        return sum(1 for p in self.problems if p.state == "new")

    @property
    def existing_count(self) -> int:
        return sum(1 for p in self.problems if p.state == "existing")

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "version": self.version,
            "sections": self.sections,
            "problems": [p.__dict__ for p in self.problems],
            "test_case_count": self.test_case_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "new_count": self.new_count,
            "existing_count": self.existing_count,
            "valid": self.valid,
        }


@dataclass
class ImportResult:
    sheet: object = None
    created: int = 0
    updated: int = 0
    skipped: int = 0
    test_cases: int = 0
    sections: int = 0
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    dry_run: bool = False

    def summary(self) -> str:
        return (
            f"New problems: {self.created}\n"
            f"Updated problems: {self.updated}\n"
            f"Skipped duplicates: {self.skipped}\n"
            f"Sections imported: {self.sections}\n"
            f"Test cases imported: {self.test_cases}"
        )


# ---------------------------------------------------------------------------
# Normalisation helpers (shared by every format)
# ---------------------------------------------------------------------------


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v not in (None, "")]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,\n;|]", value) if part.strip()]
    return [value]


def normalize_difficulty(value) -> str:
    if not value:
        return Difficulty.EASY
    text = str(value).strip().lower()
    if text in VALID_DIFFICULTIES:
        return VALID_DIFFICULTIES[text]
    return VALID_DIFFICULTY_ALIASES.get(text, Difficulty.EASY)


def normalize_mode(value) -> str:
    if not value:
        return ExecutionMode.FUNCTION
    text = str(value).strip().lower()
    return MODE_ALIASES.get(text, ExecutionMode.FUNCTION)


def normalize_param_spec(value):
    """Accept ``["int[]", "int"]`` or ``[{"name": "nums", "type": "int[]"}]``."""
    if not value:
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1]
        value = [p for p in re.split(r",(?![^()\[\]]*[)\]])", text) if p.strip()]
    out = []
    for item in value:
        if isinstance(item, dict):
            type_name = normalize_type(item.get("type") or item.get("spec") or "")
            name = (item.get("name") or "").strip()
            if not type_name:
                continue
            out.append({"name": name, "type": type_name} if name else type_name)
        else:
            type_name = normalize_type(item)
            if type_name:
                out.append(type_name)
    return out


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def make_slug(title: str, external_id=None) -> str:
    base = slugify(title)[:200]
    if not base and external_id:
        base = f"problem-{slugify(str(external_id))}"
    return base or "problem"


def normalize_test_cases(raw_cases, warnings: list, title: str, default_checker: str = "") -> list:
    cases = []
    for index, raw in enumerate(raw_cases or []):
        if isinstance(raw, str):
            raw = {"input": raw}
        if not isinstance(raw, dict):
            warnings.append(f"{title}: test case {index + 1} is not an object, skipped.")
            continue
        input_data = raw.get("input", raw.get("input_data", raw.get("args", "")))
        expected = raw.get(
            "expected_output", raw.get("expected", raw.get("output", raw.get("answer", "")))
        )
        if input_data in (None, ""):
            warnings.append(f"{title}: test case {index + 1} has no input, skipped.")
            continue
        comparison = str(raw.get("comparison", "") or "").strip().lower()
        if comparison not in VALID_COMPARISON_MODES:
            comparison = COMPARISON_EXACT
        checker = str(raw.get("checker", default_checker) or "").strip().lower()
        if checker and checker not in VALID_CHECKERS:
            warnings.append(
                f"{title}: test case {index + 1} names unknown checker {checker!r}, "
                "falling back to output comparison."
            )
            checker = ""
        cases.append(
            {
                "name": str(raw.get("name", "") or "").strip(),
                "input_data": "" if input_data is None else str(input_data).strip(),
                "expected_output": "" if expected is None else str(expected).strip(),
                "explanation": str(raw.get("explanation", "") or ""),
                "is_sample": bool(raw.get("is_sample", raw.get("sample", False))),
                "is_hidden": bool(raw.get("is_hidden", raw.get("hidden", False))),
                "order": int(raw.get("order", index) or index),
                "comparison": comparison,
                "checker": checker,
            }
        )
    # The first few cases become the visible samples unless stated otherwise.
    for index, case in enumerate(cases):
        if not case["is_sample"] and not case["is_hidden"] and index < 3:
            case["is_sample"] = True
    return cases


def normalize_problem(raw: dict, warnings: list, section_name: str = "") -> dict:
    if not isinstance(raw, dict):
        warnings.append(f"{section_name or 'Sheet'}: problem entry is not an object, skipped.")
        return {}

    title = clean_title(raw.get("title") or raw.get("name") or "")
    if not title:
        warnings.append(f"{section_name or 'Sheet'}: a problem has no title, skipped.")
        return {}

    domains = [clean_title(d) for d in as_list(raw.get("domains") or raw.get("domain") or raw.get("category"))]
    tags = [clean_title(t) for t in as_list(raw.get("tags") or raw.get("tag") or raw.get("topics"))]
    if raw.get("topic"):
        tags.extend(clean_title(t) for t in as_list(raw.get("topic")))

    external_id = str(raw.get("external_id") or raw.get("problem_id") or raw.get("leetcode_id") or "").strip()

    default_checker = str(raw.get("checker", "") or "").strip().lower()
    if default_checker and default_checker not in VALID_CHECKERS:
        warnings.append(
            f"{title}: unknown checker {default_checker!r}, test cases fall back to "
            "output comparison."
        )
        default_checker = ""
    param_spec = normalize_param_spec(raw.get("param_spec") or raw.get("params") or raw.get("signature"))
    return_spec = normalize_type(raw.get("return_spec") or raw.get("return_type") or "")
    for position, item in enumerate(param_spec):
        type_name = item["type"] if isinstance(item, dict) else item
        if not type_name:
            continue
        if TypeSpec(type_name).kind == "unknown":
            warnings.append(
                f"{title}: parameter {position + 1} has unsupported type {type_name!r}; "
                "the judge will pass it through unchanged."
            )
    if return_spec and TypeSpec(return_spec).kind == "unknown":
        warnings.append(
            f"{title}: unsupported return type {return_spec!r}; the judge will pass it "
            "through unchanged."
        )

    return {
        "title": title,
        "slug": (raw.get("slug") or "").strip() or make_slug(title, external_id),
        "external_id": external_id,
        "description": str(raw.get("description") or raw.get("content") or "").strip(),
        "difficulty": normalize_difficulty(raw.get("difficulty") or raw.get("level")),
        "domains": [d for d in domains if d],
        "tags": [t for t in tags if t],
        "constraints": str(raw.get("constraints") or "").strip(),
        "input_format": str(raw.get("input_format") or "").strip(),
        "output_format": str(raw.get("output_format") or "").strip(),
        "examples": str(raw.get("examples") or "").strip(),
        "hints": str(raw.get("hints") or "").strip(),
        "explanation": str(raw.get("explanation") or raw.get("solution_explanation") or "").strip(),
        "notes": str(raw.get("notes") or "").strip(),
        "source": str(raw.get("source") or "").strip(),
        "source_url": str(raw.get("source_url") or "").strip(),
        "execution_mode": normalize_mode(raw.get("execution_mode") or raw.get("mode")),
        "function_name": str(raw.get("function_name") or raw.get("function") or "solution").strip() or "solution",
        "param_spec": param_spec,
        "return_spec": return_spec,
        "time_limit": _as_float(raw.get("time_limit")),
        "memory_limit_mb": _as_int(raw.get("memory_limit_mb")),
        "expected_time_complexity": str(
            raw.get("expected_time_complexity") or raw.get("time_complexity") or ""
        ).strip(),
        "expected_space_complexity": str(
            raw.get("expected_space_complexity") or raw.get("space_complexity") or ""
        ).strip(),
        "test_cases": normalize_test_cases(
            raw.get("test_cases") or raw.get("tests") or raw.get("cases"),
            warnings,
            title,
            default_checker,
        ),
        "starter_code": {
            str(k).strip().lower(): str(v)
            for k, v in (raw.get("starter_code") or raw.get("code_templates") or {}).items()
            if v
        },
        "is_active": bool(raw.get("is_active", True)),
    }


def _as_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _as_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def strip_html(value: str) -> str:
    """Very small HTML-to-text pass for imported descriptions."""
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------------------
# Base importer
# ---------------------------------------------------------------------------


class BaseImporter:
    """Base class: subclasses implement :meth:`parse`."""

    format_name = "base"
    label = "Base"

    def __init__(self, *, update_existing: bool = True, dry_run: bool = False, user=None):
        self.update_existing = update_existing
        self.dry_run = dry_run
        self.user = user

    # -- subclass hook -----------------------------------------------------
    def parse(self, raw_text: str) -> dict:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- shared ------------------------------------------------------------
    def normalize(self, data: dict) -> dict:
        warnings: list[str] = []
        sections = []
        for index, raw_section in enumerate(data.get("sections") or []):
            if isinstance(raw_section, list):  # tolerate ["Arrays", [...]]
                raw_section = {"name": "Section", "problems": raw_section}
            name = clean_title(raw_section.get("name") or raw_section.get("title") or f"Section {index + 1}")
            problems = []
            for raw_problem in raw_section.get("problems") or []:
                problem = normalize_problem(raw_problem, warnings, name)
                if problem:
                    problems.append(problem)
            sections.append(
                {
                    "name": name,
                    "order": int(raw_section.get("order", index) or index),
                    "description": str(raw_section.get("description") or "").strip(),
                    "problems": problems,
                }
            )

        loose = []
        for raw_problem in data.get("problems") or []:
            problem = normalize_problem(raw_problem, warnings)
            if problem:
                loose.append(problem)

        return {
            "name": clean_title(data.get("name") or "Imported sheet"),
            "description": str(data.get("description") or "").strip(),
            "source": str(data.get("source") or "Imported").strip(),
            "source_url": str(data.get("source_url") or "").strip(),
            "version": str(data.get("version") or "1.0").strip(),
            "sections": sections,
            "problems": loose,
            "warnings": warnings,
        }

    def preview(self, raw_text: str) -> ImportPreview:
        try:
            payload = self.normalize(self.parse(raw_text))
        except ImportValidationError as exc:
            return ImportPreview(valid=False, errors=[str(exc)])
        except Exception as exc:  # malformed JSON, wrong shape, ...
            return ImportPreview(valid=False, errors=[f"Could not read the file: {exc}"])

        preview = ImportPreview(
            name=payload["name"],
            description=payload["description"],
            source=payload["source"],
            version=payload["version"],
            warnings=payload["warnings"],
            payload=payload,
        )
        preview.sections = [
            {
                "name": section["name"],
                "order": section["order"],
                "problem_count": len(section["problems"]),
            }
            for section in payload["sections"]
        ]

        for section in payload["sections"]:
            for problem in section["problems"]:
                self._add_preview(problem, preview, section["name"])
        for problem in payload["problems"]:
            self._add_preview(problem, preview, "")
        return preview

    def _add_preview(self, problem: dict, preview: ImportPreview, section_name: str):
        existing = find_existing_problem(problem)
        preview.problems.append(
            ProblemPreview(
                title=problem["title"],
                slug=problem["slug"],
                state="existing" if existing else "new",
                domains=problem["domains"],
                difficulty=problem["difficulty"],
                test_cases=len(problem["test_cases"]),
                reason=(
                    f"matched existing problem '{existing.title}'"
                    if existing
                    else section_name
                ),
            )
        )
        preview.test_case_count += len(problem["test_cases"])

    def apply(self, raw_text: str) -> ImportResult:
        preview = self.preview(raw_text)
        if not preview.valid:
            raise ImportValidationError("; ".join(preview.errors))
        return self.apply_payload(preview.payload, dry_run=self.dry_run)

    def apply_payload(self, payload: dict, dry_run: bool = False) -> ImportResult:
        result = ImportResult(dry_run=dry_run or self.dry_run, warnings=list(payload.get("warnings", [])))
        context = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "test_cases": 0,
            "domains": Domain.objects.none(),
        }

        if dry_run or self.dry_run:
            for section in payload["sections"]:
                for problem in section["problems"]:
                    self._count_only(problem, context, result)
            for problem in payload["problems"]:
                self._count_only(problem, context, result)
            result.sections = len(payload["sections"])
            return result

        with transaction.atomic():
            from apps.sheets.models import Sheet, SheetProblem, SheetSection

            sheet = None
            if payload.get("name"):
                sheet, _ = Sheet.objects.get_or_create(
                    name=payload["name"],
                    defaults={
                        "description": payload.get("description", ""),
                        "source": payload.get("source", "Imported"),
                        "source_url": payload.get("source_url", ""),
                        "version": payload.get("version", "1.0"),
                    },
                )
                changed = []
                for field, value in (
                    ("description", payload.get("description")),
                    ("source", payload.get("source")),
                    ("source_url", payload.get("source_url")),
                    ("version", payload.get("version")),
                ):
                    if value and getattr(sheet, field) != value:
                        setattr(sheet, field, value)
                        changed.append(field)
                if changed:
                    sheet.save(update_fields=changed + ["updated_at"])
            result.sheet = sheet

            for section_payload in payload["sections"]:
                section = None
                if sheet:
                    section, _ = SheetSection.objects.get_or_create(
                        sheet=sheet,
                        slug=slugify(section_payload["name"])[:200],
                        defaults={
                            "name": section_payload["name"],
                            "order": section_payload["order"],
                            "description": section_payload["description"],
                        },
                    )
                    result.sections += 1
                for order, problem_payload in enumerate(section_payload["problems"]):
                    problem, outcome, test_count = self._upsert_problem(problem_payload, result)
                    _bump(context, outcome)
                    result.test_cases += test_count
                    if section and problem:
                        link, created = SheetProblem.objects.get_or_create(
                            section=section,
                            problem=problem,
                            defaults={"order": order},
                        )
                        if not created and link.order != order:
                            link.order = order
                            link.save(update_fields=["order"])

            for order, problem_payload in enumerate(payload["problems"]):
                problem, outcome, test_count = self._upsert_problem(problem_payload, result)
                _bump(context, outcome)
                result.test_cases += test_count

        result.created = context["created"]
        result.updated = context["updated"]
        result.skipped = context["skipped"]
        return result

    # -- internals ---------------------------------------------------------
    def _count_only(self, problem: dict, context: dict, result: ImportResult):
        existing = find_existing_problem(problem)
        if existing and not self.update_existing:
            _bump(context, "skipped")
        elif existing:
            _bump(context, "updated")
        else:
            _bump(context, "created")
        result.test_cases += len(problem["test_cases"])

    def _upsert_problem(self, payload: dict, result: ImportResult):
        existing = find_existing_problem(payload)
        if existing and not self.update_existing:
            return existing, "skipped", 0

        if existing:
            for field in (
                "description",
                "difficulty",
                "constraints",
                "input_format",
                "output_format",
                "examples",
                "hints",
                "explanation",
                "execution_mode",
                "function_name",
                "return_spec",
                "expected_time_complexity",
                "expected_space_complexity",
                "external_id",
                "source",
                "source_url",
                "is_active",
            ):
                value = payload.get(field)
                if value not in (None, "", []):
                    setattr(existing, field, value)
            if payload.get("param_spec"):
                existing.param_spec = payload["param_spec"]
            if payload.get("time_limit"):
                existing.time_limit = payload["time_limit"]
            if payload.get("memory_limit_mb"):
                existing.memory_limit_mb = payload["memory_limit_mb"]
            existing.save()
            outcome = "updated"
        else:
            existing = Problem.objects.create(
                title=payload["title"],
                slug=payload["slug"],
                description=payload.get("description", ""),
                difficulty=payload.get("difficulty", Difficulty.EASY),
                constraints=payload.get("constraints", ""),
                input_format=payload.get("input_format", ""),
                output_format=payload.get("output_format", ""),
                examples=payload.get("examples", ""),
                hints=payload.get("hints", ""),
                explanation=payload.get("explanation", ""),
                execution_mode=payload.get("execution_mode", ExecutionMode.FUNCTION),
                function_name=payload.get("function_name", "solution"),
                param_spec=payload.get("param_spec") or [],
                return_spec=payload.get("return_spec", ""),
                expected_time_complexity=payload.get("expected_time_complexity", ""),
                expected_space_complexity=payload.get("expected_space_complexity", ""),
                time_limit=payload.get("time_limit"),
                memory_limit_mb=payload.get("memory_limit_mb"),
                external_id=payload.get("external_id", ""),
                source=payload.get("source") or "Imported",
                source_url=payload.get("source_url", ""),
                is_active=payload.get("is_active", True),
                notes=payload.get("notes", ""),
            )
            outcome = "created"

        sync_domains_and_tags(existing, payload)
        test_count = sync_test_cases(existing, payload["test_cases"])
        sync_starter_codes(existing, payload["starter_code"])
        return existing, outcome, test_count


def _bump(context: dict, outcome: str):
    if outcome in context:
        context[outcome] += 1


# ---------------------------------------------------------------------------
# Database helpers reused by importers and the admin
# ---------------------------------------------------------------------------


def find_existing_problem(payload: dict):
    """Locate a problem by slug, then external id, then title."""
    slug = payload.get("slug")
    if slug:
        existing = Problem.objects.filter(slug=slug).first()
        if existing:
            return existing
    external_id = payload.get("external_id")
    if external_id:
        existing = Problem.objects.filter(external_id=str(external_id)).first()
        if existing:
            return existing
    title = payload.get("title")
    if title:
        return Problem.objects.filter(title__iexact=title).first()
    return None


def sync_domains_and_tags(problem, payload: dict):
    domains = []
    for name in payload.get("domains") or []:
        domain, _ = Domain.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
        domains.append(domain)
    if domains:
        problem.domains.set(domains)
        problem.primary_domain = domains[0]
        problem.save(update_fields=["primary_domain", "updated_at"])
    elif problem.domains.exists():
        problem.primary_domain = problem.domains.first()
        problem.save(update_fields=["primary_domain", "updated_at"])

    tags = []
    for name in payload.get("tags") or []:
        tag, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
        tags.append(tag)
    if tags:
        problem.tags.set(tags)


def _test_case_key(raw: str) -> str:
    """Canonical identity of a test case payload.

    Two payloads that parse to the same JSON describe the same test, even when
    they are formatted differently, so re-importing a fixed file does not leave
    stale duplicates behind.
    """
    text = (raw or "").strip()
    try:
        return json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return " ".join(text.split())


def sync_test_cases(problem, cases: list, replace: bool = False) -> int:
    """Add missing cases and refresh the ones that already exist.

    A case is identified by its input.  When the same input comes back with a
    different expected output the stored expectation is corrected, so fixing a
    typo in a sheet file and re-importing actually repairs the database instead
    of leaving the stale and the new case side by side.
    """
    if not cases:
        return 0
    if replace:
        problem.test_cases.all().delete()
    existing = {}
    # Older imports could have stored the same input twice with different
    # expectations; keep the first and drop the rest.
    for test_case in problem.test_cases.all():
        key = _test_case_key(test_case.input_data)
        if key in existing:
            test_case.delete()
        else:
            existing[key] = test_case
    created = 0
    seen = set()
    for case in cases:
        key = _test_case_key(case["input_data"])
        seen.add(key)
        if key in existing:
            test_case = existing[key]
            changed = []
            for field in ("expected_output", "name", "explanation", "comparison", "checker"):
                # A present key is authoritative even when its value is empty, so
                # dropping a checker from the source really clears it.
                if field not in case:
                    continue
                value = case[field]
                if value in (None, ""):
                    value = ""
                if getattr(test_case, field) != value:
                    setattr(test_case, field, value)
                    changed.append(field)
            if case["is_sample"] != test_case.is_sample:
                test_case.is_sample = case["is_sample"]
                changed.append("is_sample")
            if case["is_hidden"] != test_case.is_hidden:
                test_case.is_hidden = case["is_hidden"]
                changed.append("is_hidden")
            if case["order"] != test_case.order:
                test_case.order = case["order"]
                changed.append("order")
            if changed:
                test_case.save(update_fields=changed)
            continue
        TestCase.objects.create(
            problem=problem,
            name=case["name"],
            input_data=case["input_data"],
            expected_output=case["expected_output"],
            explanation=case["explanation"],
            is_sample=case["is_sample"],
            is_hidden=case["is_hidden"],
            order=case["order"],
            comparison=case.get("comparison", COMPARISON_EXACT),
            checker=case.get("checker", ""),
        )
        created += 1
    # The import is authoritative: cases that are no longer in the source are
    # dropped so corrected payloads replace their predecessors.
    for key, test_case in existing.items():
        if key not in seen:
            test_case.delete()
    return created


def sync_starter_codes(problem, starter_code: dict, overwrite: bool = False):
    """Store explicit templates, and fill the gaps with generated ones."""
    from apps.execution.models import Language
    from apps.problems.models import ProblemStarterCode

    languages = {lang.slug: lang for lang in Language.objects.enabled()}

    for slug, code in (starter_code or {}).items():
        language = languages.get(str(slug).lower())
        if not language:
            continue
        existing = ProblemStarterCode.objects.filter(problem=problem, language=language).first()
        if existing and not overwrite:
            continue
        if existing:
            existing.starter_code = code
            existing.save(update_fields=["starter_code"])
        else:
            ProblemStarterCode.objects.create(
                problem=problem, language=language, starter_code=code
            )

    for language in languages.values():
        if ProblemStarterCode.objects.filter(problem=problem, language=language).exists():
            continue
        try:
            code = generate_starter(problem, language)
        except Exception:  # pragma: no cover - defensive
            continue
        ProblemStarterCode.objects.create(
            problem=problem, language=language, starter_code=code
        )
