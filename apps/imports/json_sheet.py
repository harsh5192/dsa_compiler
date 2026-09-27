"""JSON sheet importer.

Expected shape (extra keys are ignored, missing keys get sensible defaults)::

    {
      "name": "My DSA Sheet",
      "description": "Custom DSA sheet",
      "source": "Custom",
      "sections": [
        {"name": "Arrays", "order": 1, "problems": [ ... ]}
      ]
    }

A bare list of problems is also accepted, as is ``{"problems": [...]}``.
"""

from __future__ import annotations

import json

from .base import BaseImporter, ImportValidationError


class JSONSheetImporter(BaseImporter):
    format_name = "json"
    label = "JSON"

    def parse(self, raw_text: str) -> dict:
        if not (raw_text or "").strip():
            raise ImportValidationError("The file is empty.")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ImportValidationError(f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).")

        if isinstance(data, list):
            return {"name": "Imported sheet", "problems": data}
        if not isinstance(data, dict):
            raise ImportValidationError("The top level of a sheet file must be an object or a list.")

        if not any(key in data for key in ("sections", "problems")):
            raise ImportValidationError(
                "The file has no 'sections' or 'problems' key. "
                "See the README for the expected structure."
            )
        return data
