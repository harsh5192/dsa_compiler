"""Output comparison.

Test-case expectations are stored as text so they stay editable and diffable
(``[0,1]``, ``4``, ``"abc"``, ``true``).  Comparison first tries a structural
JSON comparison, which makes formatting irrelevant and tolerates differences
such as ``4`` vs ``4.0`` or ``[1,2,3]`` vs ``[1,2,3,null,null]``.  When either
side is not JSON (stdin-style problems) it falls back to whitespace-insensitive
string comparison.
"""

from __future__ import annotations

import json
import re


def canonical(value, unordered: bool = False):
    """Normalise a decoded JSON value for comparison.

    With ``unordered=True`` nested lists are sorted after normalisation, which
    lets a "return the groups" problem accept any group ordering.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        items = [canonical(v, unordered) for v in value]
        while items and items[-1] is None:
            items.pop()
        if unordered:
            items.sort(key=_sort_key)
        return items
    if isinstance(value, dict):
        return {k: canonical(v, unordered) for k, v in sorted(value.items())}
    if isinstance(value, str):
        return value.strip()
    return value


def _sort_key(value):
    """Total ordering over mixed JSON values so ``list.sort`` never raises."""
    if isinstance(value, bool):
        return (0, float(value), "")
    if isinstance(value, (int, float)):
        return (1, float(value), "")
    if isinstance(value, str):
        return (2, 0.0, value)
    if value is None:
        return (3, 0.0, "")
    return (4, 0.0, json.dumps(value, sort_keys=True, default=str))


def _maybe_json(text: str, unordered: bool = False):
    if text is None:
        return None
    candidate = text.strip()
    if not candidate:
        return None
    if candidate[0] not in "[{\"-0123456789tfn":
        return None
    try:
        return canonical(json.loads(candidate), unordered)
    except (json.JSONDecodeError, ValueError):
        return None


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def outputs_match(actual: str, expected: str, comparison: str = "exact") -> bool:
    """True when a program's stdout satisfies the expected output."""
    unordered = (comparison or "exact") == "unordered"
    a, e = _maybe_json(actual, unordered), _maybe_json(expected, unordered)
    if a is not None and e is not None:
        return a == e
    if e is not None:
        # Expected parses but actual does not -> fall through to text compare
        # only when the raw texts agree.
        return collapse_whitespace(actual) == collapse_whitespace(expected)
    if a is not None and actual.strip() == (expected or "").strip():
        return True
    return collapse_whitespace(actual) == collapse_whitespace(expected)


def format_output(text: str, limit: int = 4000) -> str:
    text = text or ""
    if len(text) > limit:
        return text[:limit] + f"\n... ({len(text) - limit} more characters)"
    return text
