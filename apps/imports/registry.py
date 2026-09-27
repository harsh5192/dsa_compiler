"""Importer registry.

Adding a new source means writing a ``BaseImporter`` subclass and adding it to
:data:`IMPORTERS`.  Nothing else in the application needs to change.
"""

from __future__ import annotations

from .base import BaseImporter, ImportValidationError
from .csv_sheet import CSVSheetImporter
from .json_sheet import JSONSheetImporter
from .leetcode import LeetCodeImporter

IMPORTERS: dict[str, type[BaseImporter]] = {
    "json": JSONSheetImporter,
    "csv": CSVSheetImporter,
    "leetcode": LeetCodeImporter,
    "custom": JSONSheetImporter,
    "backup": JSONSheetImporter,
}


def get_importer(format_name: str, **kwargs) -> BaseImporter:
    try:
        importer_class = IMPORTERS[(format_name or "json").lower()]
    except KeyError as exc:
        raise ImportValidationError(
            f"Unknown import format '{format_name}'. Available: {', '.join(sorted(IMPORTERS))}."
        ) from exc
    return importer_class(**kwargs)


def available_formats() -> list[dict]:
    seen = {}
    for key, importer_class in IMPORTERS.items():
        seen.setdefault(importer_class, []).append(key)
    return [
        {
            "value": keys[0],
            "aliases": keys[1:],
            "label": importer_class.label,
            "class_name": importer_class.__name__,
        }
        for importer_class, keys in seen.items()
    ]
