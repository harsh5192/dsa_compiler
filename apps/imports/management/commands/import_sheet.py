"""Import a DSA sheet from a JSON or CSV file.

Examples::

    python manage.py import_sheet data/sheets/striver_a2z.json
    python manage.py import_sheet data/sheets/striver_a2z.json --dry-run
    python manage.py import_sheet my_sheet.csv --format csv
    python manage.py import_sheet leetcode_export.json --format leetcode
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.imports.base import ImportValidationError
from apps.imports.models import ImportFormat, ImportJob, ImportStatus
from apps.imports.registry import get_importer


class Command(BaseCommand):
    help = "Import a DSA sheet (JSON/CSV) or a LeetCode-style problem file."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the file to import.")
        parser.add_argument(
            "--format",
            dest="import_format",
            default="",
            help="json | csv | leetcode (auto-detected from the extension by default).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing anything.",
        )
        parser.add_argument(
            "--no-update",
            action="store_true",
            help="Skip problems that already exist instead of updating them.",
        )
        parser.add_argument(
            "--quiet-preview",
            action="store_true",
            help="Do not print the per-problem preview table.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser()
        if not path.exists():
            raise CommandError(f"No such file: {path}")

        import_format = options["import_format"] or ("csv" if path.suffix.lower() == ".csv" else "json")
        try:
            raw_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw_text = path.read_text(encoding="utf-8", errors="replace")

        importer = get_importer(
            import_format,
            update_existing=not options["no_update"],
            dry_run=options["dry_run"],
        )

        try:
            preview = importer.preview(raw_text)
        except ImportValidationError as exc:
            self._record(path, import_format, status=ImportStatus.FAILED, errors=[str(exc)])
            raise CommandError(str(exc)) from exc

        if not preview.valid:
            for error in preview.errors:
                self.stderr.write(self.style.ERROR(error))
            self._record(path, import_format, status=ImportStatus.FAILED, errors=preview.errors)
            raise CommandError("; ".join(preview.errors))

        self.stdout.write(f"File      : {path}")
        self.stdout.write(f"Format    : {importer.label}")
        self.stdout.write(f"Sheet     : {preview.name}")
        self.stdout.write(f"Sections  : {len(preview.sections)}")
        self.stdout.write(f"Problems  : {len(preview.problems)}")
        self.stdout.write(f"Test cases: {preview.test_case_count}")
        self.stdout.write(
            f"Duplicate : {preview.existing_count} existing, {preview.new_count} new"
        )
        for warning in preview.warnings[:20]:
            self.stdout.write(self.style.WARNING(f"  warning: {warning}"))
        if len(preview.warnings) > 20:
            self.stdout.write(f"  ... and {len(preview.warnings) - 20} more warnings")

        if not options["quiet_preview"] and preview.problems:
            self.stdout.write("")
            self.stdout.write(f"{'#':>4}  {'state':<9} {'difficulty':<9} {'tests':>5}  title")
            for index, problem in enumerate(preview.problems, start=1):
                self.stdout.write(
                    f"{index:>4}  {problem.state:<9} {problem.difficulty:<9} "
                    f"{problem.test_cases:>5}  {problem.title}"
                )

        if options["dry_run"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Dry run: nothing was written."))
            self._record(
                path,
                import_format,
                status=ImportStatus.VALIDATED,
                dry_run=True,
                created=preview.new_count,
                updated=preview.existing_count,
                test_case_count=preview.test_case_count,
                warnings=preview.warnings,
            )
            return

        result = importer.apply_payload(preview.payload)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import completed"))
        self.stdout.write(result.summary())
        self._record(
            path,
            import_format,
            status=ImportStatus.IMPORTED,
            sheet=result.sheet,
            created=result.created,
            updated=result.updated,
            skipped=result.skipped,
            test_case_count=result.test_cases,
            section_count=result.sections,
            warnings=result.warnings,
        )

    def _record(self, path, import_format, *, status, errors=None, **kwargs):
        job = ImportJob(
            source_file=str(path),
            import_format=(
                ImportFormat.CSV
                if import_format == "csv"
                else ImportFormat.LEETCODE
                if import_format == "leetcode"
                else ImportFormat.JSON
            ),
            status=status,
            errors=errors or [],
            message=json.dumps(kwargs, default=str),
            **kwargs,
        )
        job.save()
        return job
