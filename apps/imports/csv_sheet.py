"""CSV sheet importer.

The CSV carries one problem per row.  Multi-value columns use ``|`` as the
separator.  A sheet's section structure comes from the ``section`` column and
the row order, so a spreadsheet is enough to define a whole sheet.

Recognised columns (case-insensitive, extra columns are ignored)::

    title, slug, difficulty, domains, tags, section, description, constraints,
    input_format, output_format, examples, hints, explanation, function_name,
    param_spec, return_spec, execution_mode, expected_time_complexity,
    expected_space_complexity, external_id, time_limit, memory_limit_mb,
    test_input, test_output, test_is_sample, test_is_hidden
"""

from __future__ import annotations

import csv
import io
import json

from .base import BaseImporter, ImportValidationError


class CSVSheetImporter(BaseImporter):
    format_name = "csv"
    label = "CSV"

    MULTI_COLUMNS = {"domains", "tags", "param_spec", "starter_code", "domains", "tags"}

    def parse(self, raw_text: str) -> dict:
        if not (raw_text or "").strip():
            raise ImportValidationError("The file is empty.")
        try:
            dialect = csv.Sniffer().sniff(raw_text[:4096], delimiters=",;\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter)
        if not reader.fieldnames:
            raise ImportValidationError("The CSV has no header row.")
        if not any(name and name.strip().lower() in ("title", "name", "problem") for name in reader.fieldnames):
            raise ImportValidationError(
                "The CSV needs a 'title' (or 'name' / 'problem') column."
            )

        rows = list(reader)
        if not rows:
            raise ImportValidationError("The CSV contains no data rows.")

        sheet_name = ""
        description = ""
        source = "CSV import"
        sections: dict[str, list] = {}
        order: list[str] = []
        problems: list[dict] = []

        for row_index, row in enumerate(rows, start=2):
            clean = {
                (key or "").strip().lower(): (value.strip() if isinstance(value, str) else value)
                for key, value in row.items()
            }
            section_name = clean.get("section") or clean.get("section_name") or ""
            if not sheet_name and clean.get("sheet_name"):
                sheet_name = clean["sheet_name"]
            if not description and clean.get("sheet_description"):
                description = clean["sheet_description"]
            if not source and clean.get("source"):
                source = clean["source"]

            problem = self._row_to_problem(clean, row_index)
            if problem is None:
                continue
            if section_name:
                if section_name not in sections:
                    sections[section_name] = []
                    order.append(section_name)
                sections[section_name].append(problem)
            else:
                problems.append(problem)

        return {
            "name": sheet_name or "Imported CSV sheet",
            "description": description,
            "source": source,
            "sections": [
                {"name": name, "order": index, "problems": sections[name]}
                for index, name in enumerate(order)
            ],
            "problems": problems,
        }

    def _row_to_problem(self, row: dict, row_index: int):
        title = row.get("title") or row.get("name") or row.get("problem")
        if not title:
            return None

        problem = {
            "title": title,
            "slug": row.get("slug") or "",
            "external_id": row.get("external_id") or row.get("id") or "",
            "description": row.get("description") or "",
            "difficulty": row.get("difficulty") or row.get("level") or "",
            "domains": _split(row.get("domains") or row.get("domain")),
            "tags": _split(row.get("tags") or row.get("tag") or row.get("topics")),
            "constraints": row.get("constraints") or "",
            "input_format": row.get("input_format") or "",
            "output_format": row.get("output_format") or "",
            "examples": row.get("examples") or "",
            "hints": row.get("hints") or "",
            "explanation": row.get("explanation") or "",
            "function_name": row.get("function_name") or "",
            "param_spec": row.get("param_spec") or "",
            "return_spec": row.get("return_spec") or "",
            "execution_mode": row.get("execution_mode") or "",
            "expected_time_complexity": row.get("expected_time_complexity") or "",
            "expected_space_complexity": row.get("expected_space_complexity") or "",
            "time_limit": row.get("time_limit") or "",
            "memory_limit_mb": row.get("memory_limit_mb") or "",
        }

        test_input = row.get("test_input") or row.get("input")
        if test_input:
            problem["test_cases"] = [
                {
                    "input": test_input,
                    "expected_output": row.get("test_output") or row.get("expected_output") or "",
                    "is_sample": _as_bool(row.get("test_is_sample"), default=True),
                    "is_hidden": _as_bool(row.get("test_is_hidden"), default=False),
                    "name": row.get("test_name") or "",
                }
            ]
        return problem


def _split(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in text.replace(";", "|").split("|") if part.strip()]


def _as_bool(value, default=False):
    if value in (None, ""):
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")
