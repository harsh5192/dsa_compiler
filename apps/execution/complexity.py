"""Heuristic complexity estimation.

**These numbers are estimates, not measurements.**  Runtime alone cannot
identify a Big-O class: an O(n log n) and an O(n^2) solution can both take
4 ms on a 20-element input.  What this module does instead is read the source
and look for structural patterns whose cost is well understood, then reports a
confidence level so the UI can be honest about how much to trust the result.

It is intentionally a *static* heuristic.  For the authoritative answer, each
problem stores ``expected_time_complexity`` / ``expected_space_complexity``
which come from a reference solution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Loop keywords we recognise, per family.
_LOOP_RE = re.compile(
    r"\b(?:for|while|foreach|do)\s*[\(\{]?", re.IGNORECASE
)
_COMMENT_RE = re.compile(r"//.*?$|#.*?$|/\*.*?\*/", re.DOTALL | re.MULTILINE)
_STRING_RE = re.compile(r"\"(\\.|[^\"\\])*\"|'(\\.|[^'\\])*'")

HASH_USE = re.compile(
    r"\b(?:unordered_map|unordered_set|hashmap|hashset|dict|setdefault|"
    r"getOrDefault|putIfAbsent|defaultdict|Map<|Set<)\b",
    re.IGNORECASE,
)
SORT_CALL = re.compile(
    r"\b(?:sort|sorted|std::sort|Arrays\.sort|prioritySort|quickSort|mergeSort|"
    r"heapify|make_heap)\s*\(|\.sort\s*\(",
    re.IGNORECASE,
)
RECURSION_RE = re.compile(
    r"\b(\w+)\s*\([^)]*\)\s*\{[^}]*\b\1\s*\(", re.DOTALL
)
HASHTABLE_RE = re.compile(r"\[\s*\d+\s*\]")
NESTED_LOOP_RE = re.compile(
    r"(?:for|while)\s*\([^)]*\)\s*\{[^{}]*?(?:for|while)\s*\(", re.DOTALL
)
SORT_CALL_LOWER = SORT_CALL


@dataclass
class ComplexityEstimate:
    time: str = "O(?)"
    space: str = "O(?)"
    confidence: str = "Low"
    notes: list = field(default_factory=list)
    signals: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "space": self.space,
            "confidence": self.confidence,
            "notes": self.notes,
            "signals": self.signals,
        }


def strip_noise(source: str) -> str:
    """Remove comments and string literals so they do not skew the analysis."""
    if not source:
        return ""
    without_block = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)
    without_line = re.sub(r"(?m)^\s*(?://|#).*?$", " ", without_block)
    return _STRING_RE.sub(' "" ', without_line)


def count_loop_depth(source: str) -> int:
    """Maximum number of nested ``for``/``while`` bodies."""
    depth = 0
    maximum = 0
    for match in re.finditer(r"\{", source):
        prefix = source[: match.start()]
        opens = len(re.findall(r"(?:for|while|do|else if|try|switch)\b[^{}]*\{", prefix))
        closes = prefix.count("}")
        depth = max(depth, opens - closes)
        maximum = max(maximum, depth)
    return min(maximum, 4)


def detect_recursion(source: str) -> bool:
    return bool(RECURSION_RE.search(source))


def detect_function_name(source: str) -> str | None:
    match = re.search(
        r"\b(?:def|function|func|public|private|static)\s+[\w<>\[\],\s\*&]*?"
        r"(\w+)\s*\([^;{]*\)\s*\{",
        source,
    )
    return match.group(1) if match else None


def estimate_complexity(source: str, language=None) -> ComplexityEstimate:
    """Return a labelled, best-effort complexity estimate for ``source``."""
    clean = strip_noise(source)
    if not clean.strip():
        return ComplexityEstimate(notes=["No code to analyse."], confidence="Low")

    notes: list[str] = []
    signals: dict = {}

    loop_depth = count_loop_depth(clean)
    linear = len(re.findall(r"\b(?:for|while|foreach|forEach)\b", clean))
    uses_hash = bool(HASH_USE.search(clean))
    uses_sort = bool(SORT_CALL.search(clean))
    recursive = detect_recursion(clean)
    triple_loop = bool(
        re.search(
            r"(?:for|while)\s*\([^)]*\)\s*\{[^{}]*?(?:for|while)\s*\([^)]*\)\s*\{"
            r"[^{}]*?(?:for|while)\s*\(",
            clean,
            re.DOTALL,
        )
    )
    divide_and_conquer = recursive and bool(
        re.search(r"\b(?:mid|len\s*\(\s*\)\s*//|length\s*/\s*2|sz\s*>>\s*1)\b", clean)
    )

    signals.update(
        {
            "loop_depth": loop_depth,
            "loops": linear,
            "hash_table": uses_hash,
            "sorting": uses_sort,
            "recursive": recursive,
            "divide_and_conquer": divide_and_conquer,
        }
    )

    # ---- time -----------------------------------------------------------
    confidence = "Low"
    if divide_and_conquer:
        time = "O(n log n)"
        confidence = "Medium"
        notes.append("Recursion that splits the input in half usually costs O(n log n).")
    elif triple_loop:
        time = "O(n^3)"
        confidence = "Medium"
        notes.append("Three nested loops over n-sized inputs.")
    elif loop_depth >= 2:
        time = "O(n^2)"
        confidence = "Medium"
        notes.append(f"{loop_depth} nested loop levels detected.")
    elif uses_sort and linear == 0:
        time = "O(n log n)"
        confidence = "Medium"
        notes.append("A library sort was called and no explicit loop was found.")
    elif uses_sort:
        time = "O(n log n)"
        confidence = "Low"
        notes.append("Contains a sort; the surrounding loops decide the real cost.")
    elif linear >= 1 and uses_hash:
        time = "O(n)"
        confidence = "Medium"
        notes.append("Loops that iterate once over n with hash lookups average O(1) each.")
    elif linear >= 1:
        time = "O(n)"
        confidence = "Medium" if loop_depth == 1 else "Low"
        notes.append("A single pass over the input.")
    elif recursive:
        time = "O(2^n)"
        confidence = "Low"
        notes.append("Recursion without a visible halving of the input can be exponential.")
    else:
        time = "O(1)"
        confidence = "Low"
        notes.append("No loops or recursion found; treated as constant work.")

    # ---- space ----------------------------------------------------------
    space_confidence = "Low"
    if recursive:
        space = "O(n)"
        space_confidence = "Medium"
        notes.append("Recursion consumes stack space proportional to the depth.")
    elif HASHTABLE_RE.search(clean) or (uses_hash and linear):
        space = "O(n)"
        space_confidence = "Medium"
        notes.append("A container is created whose size follows the input.")
    elif re.search(r"\bnew\s+(?:List|Array|String|int|Integer|char)\s*\[", clean) or re.search(
        r"=\s*new\s+(?:ArrayList|HashMap|int\[\]|Integer\[\])", clean
    ):
        space = "O(n)"
        space_confidence = "Low"
        notes.append("An array or collection is allocated from input data.")
    elif loop_depth >= 2:
        space = "O(1)"
        notes.append("Nested loops without extra containers keep space constant.")
    else:
        space = "O(1)"

    overall = min(
        _confidence_rank(confidence), _confidence_rank(space_confidence), key=_rank_value
    )
    return ComplexityEstimate(
        time=time,
        space=space,
        confidence=overall,
        notes=notes,
        signals=signals,
    )


_RANKS = {"Low": 0, "Medium": 1, "High": 2}


def _confidence_rank(name: str) -> str:
    return name if name in _RANKS else "Low"


def _rank_value(name: str) -> int:
    return _RANKS.get(name, 0)


def compare_to_expected(
    estimate: ComplexityEstimate, expected_time: str, expected_space: str
) -> list[str]:
    """Human-readable deltas between the estimate and the reference answer."""
    notes = []
    if expected_time and estimate.time and expected_time.replace(" ", "") != estimate.time.replace(" ", ""):
        notes.append(f"Estimated time {estimate.time} differs from the expected {expected_time}.")
    if expected_space and estimate.space and expected_space.replace(" ", "") != estimate.space.replace(" ", ""):
        notes.append(f"Estimated space {estimate.space} differs from the expected {expected_space}.")
    return notes
