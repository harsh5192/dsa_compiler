"""Seed the database with the bundled languages and sheets.

Examples::

    python manage.py seed_dsa_data                 # languages + starter sheet + sheets
    python manage.py seed_dsa_data --content-only  # skip the title-only sheet index
    python manage.py seed_dsa_data --sheets-only   # skip the starter sheet
    python manage.py seed_dsa_data --dry-run       # report without writing
    python manage.py seed_dsa_data --rebuild       # regenerate data/*.json first

Everything is idempotent: re-running updates the existing rows instead of
duplicating them, so it is safe to run after every import.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.imports.registry import get_importer
from apps.problems.models import Problem

PROJECT_ROOT = settings.BASE_DIR
SHEET_DIR = PROJECT_ROOT / "data" / "sheets"
SAMPLE_FILE = PROJECT_ROOT / "data" / "samples" / "sample_problems.json"
BUILDER = PROJECT_ROOT / "tools" / "build_sheet_data.py"

#: Loaded in this order so the full-content problems exist first and the sheet
#: index entries then attach to them.
SHEET_FILES = ["striver_a2z.json", "striver_old.json", "love_babbar.json"]


class Command(BaseCommand):
    help = "Load the built-in languages and the bundled DSA sheets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate every file and report, without writing.",
        )
        parser.add_argument(
            "--content-only",
            action="store_true",
            help="Only import the starter sheet that has statements and tests.",
        )
        parser.add_argument(
            "--sheets-only",
            action="store_true",
            help="Only import the three sheet indexes.",
        )
        parser.add_argument(
            "--no-languages",
            action="store_true",
            help="Do not touch the language table.",
        )
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Run tools/build_sheet_data.py before importing.",
        )

    def handle(self, *args, **options):
        if options["rebuild"]:
            self._rebuild()

        if not options["no_languages"]:
            call_command("seed_languages", "--only-missing", verbosity=0)
            self.stdout.write(
                self.style.SUCCESS("Languages ready.")
            )

        targets: list[Path] = []
        if not options["sheets_only"]:
            targets.append(SAMPLE_FILE)
        if not options["content_only"]:
            targets.extend(SHEET_DIR / name for name in SHEET_FILES)

        if not targets:
            self.stdout.write(self.style.WARNING("Nothing selected, nothing to do."))
            return

        if options["dry_run"]:
            self._dry_run(targets)
            return

        with transaction.atomic():
            for path in targets:
                self._import(path)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {Problem.objects.count()} problems and "
                f"{self.problem_count_note()}"
            )
        )

    def problem_count_note(self) -> str:
        from apps.problems.models import TestCase

        return f"{TestCase.objects.count()} test cases in the database."

    def _rebuild(self):
        if not BUILDER.exists():
            self.stderr.write(self.style.WARNING(f"Builder not found: {BUILDER}"))
            return
        self.stdout.write(f"Rebuilding data files with {BUILDER.name} ...")
        subprocess.run(
            [sys.executable, str(BUILDER), "--quiet"], check=True, cwd=str(PROJECT_ROOT)
        )

    def _dry_run(self, targets: list[Path]):
        total = 0
        for path in targets:
            if not path.exists():
                self.stderr.write(self.style.WARNING(f"missing file, skipped: {path}"))
                continue
            importer = get_importer("json", dry_run=True)
            try:
                preview = importer.preview(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001 - report and continue
                self.stderr.write(self.style.ERROR(f"{path.name}: {exc}"))
                continue
            if not preview.valid:
                self.stderr.write(self.style.ERROR(f"{path.name}: {'; '.join(preview.errors)}"))
                continue
            total += preview.test_case_count
            self.stdout.write(
                f"{path.name:22s} {len(preview.sections):3d} sections  "
                f"{len(preview.problems):4d} problems  {preview.test_case_count:4d} test cases  "
                f"({preview.existing_count} existing)"
            )
            for warning in preview.warnings[:5]:
                self.stdout.write(self.style.WARNING(f"  warning: {warning}"))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"Dry run: {total} test cases would be imported."))

    def _import(self, path: Path):
        if not path.exists():
            self.stderr.write(self.style.WARNING(f"missing file, skipped: {path}"))
            return
        importer = get_importer("json", update_existing=True)
        try:
            result = importer.apply(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - one bad file must not kill the seed
            self.stderr.write(self.style.ERROR(f"{path.name}: import failed: {exc}"))
            return
        self.stdout.write(
            f"{path.name:22s} {result.sections:3d} sections  "
            f"{result.created:4d} new  {result.updated:4d} updated  "
            f"{result.test_cases:4d} test cases"
        )
        for warning in result.warnings[:5]:
            self.stdout.write(self.style.WARNING(f"  warning: {warning}"))
