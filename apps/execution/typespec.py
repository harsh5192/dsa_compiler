"""A tiny type language used to describe problem signatures.

Test-case inputs are always a JSON array of arguments, e.g.::

    [[2, 7, 11, 15], 9]

Python and JavaScript harnesses simply ``json.loads`` that array.  Compiled
languages need to know the *static* type of each element, so every problem
carries a ``param_spec`` list using the canonical names below::

    int  long  double  bool  string
    int[]  long[]  double[]  string[]
    int[][]  long[][]  double[][]  string[][]
    ListNode  TreeNode

Alias spellings such as ``vector<int>``, ``vector<vector<int>>``,
``Integer[]`` or ``char*`` are normalised to the canonical form so that data
imported from other tools still works.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SCALARS = ("int", "long", "double", "bool", "string")
VECTORS = ("int[]", "long[]", "double[]", "string[]")
MATRICES = ("int[][]", "long[][]", "double[][]", "string[][]")
NODES = ("ListNode", "TreeNode")

CANONICAL = SCALARS + VECTORS + MATRICES + NODES + ("void",)

#: How to spell each scalar in each compiled language.
SCALAR_MAP = {
    "cpp": {
        "int": "int",
        "long": "long long",
        "double": "double",
        "bool": "bool",
        "string": "std::string",
    },
    "java": {
        "int": "int",
        "long": "long",
        "double": "double",
        "bool": "boolean",
        "string": "String",
    },
    "c": {
        "int": "int",
        "long": "long long",
        "double": "double",
        "bool": "int",
        "string": "char*",
    },
}

_ALIASES = {
    "integer": "int",
    "int32": "int",
    "int64": "long",
    "long long": "long",
    "longlong": "long",
    "float": "double",
    "str": "string",
    "char": "string",
    "text": "string",
    "boolean": "bool",
    "number": "double",
    "listnode": "ListNode",
    "treenode": "TreeNode",
    "list": "listnode",
    "tree": "treenode",
}


#: Generic containers that mean "one element per box", i.e. a canonical ``[]``.
_CONTAINERS = (
    "vector",
    "list",
    "arraylist",
    "linkedlist",
    "array",
    "collection",
    "deque",
    "queue",
    "stack",
    "priorityqueue",
    "set",
    "listnode",
    "treenode",
)
_CONTAINER_RE = re.compile(
    r"^(?:std::)?(?:%s)\s*<(.+)>$" % "|".join(_CONTAINERS),
    re.IGNORECASE,
)


def normalize(spec: str | None) -> str:
    """Map any reasonable spelling of a type onto the canonical vocabulary."""
    if not spec:
        return ""
    raw = str(spec).strip()
    if not raw:
        return ""
    # Drop reference/const noise: "vector<int>&", "const string&", "int *"
    raw = raw.replace("const", " ").replace("&", " ").replace("*", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    # "vector<vector<int> >" -> "vector<vector<int>>"
    raw = re.sub(r"\s*([<>])\s*", r"\1", raw)
    return _normalize_type(raw)


def _normalize_type(raw: str) -> str:
    lowered = raw.lower()
    if lowered in _ALIASES:
        return _ALIASES[lowered]

    # A bare word is a type name in some spelling ("String", "Integer", "Bool").
    # Every canonical name is lower case, so fold it before giving up.
    if raw.isalpha() or (raw.replace("_", "").isalnum() and " " not in raw):
        return _ALIASES.get(lowered, lowered)

    # vector<int>, vector<vector<int>>, List<List<Integer>> -> one level per <>
    container = _CONTAINER_RE.fullmatch(raw)
    if container:
        return _normalize_type(container.group(1)) + "[]"

    # Java/JS arrays: Integer[], int[][]
    if raw.endswith("[]"):
        depth = (len(raw) - len(raw.rstrip("[]"))) // 2
        base = _normalize_type(raw[: -depth * 2].strip())
        return base + "[]" * depth

    return _ALIASES.get(lowered, raw)


@dataclass(frozen=True)
class TypeSpec:
    canonical: str

    # -- classification -----------------------------------------------------
    @property
    def is_void(self) -> bool:
        return self.canonical == "void"

    @property
    def is_scalar(self) -> bool:
        return self.canonical in SCALARS

    @property
    def is_string(self) -> bool:
        return self.canonical == "string"

    @property
    def base(self) -> str:
        return self.canonical.replace("[]", "")

    @property
    def depth(self) -> int:
        return self.canonical.count("[]")

    @property
    def kind(self) -> str:
        c = self.canonical
        if c in SCALARS:
            return "scalar"
        if c in VECTORS:
            return "vector"
        if c in MATRICES:
            return "matrix"
        if c == "ListNode":
            return "listnode"
        if c == "TreeNode":
            return "treenode"
        if c == "void":
            return "void"
        return "unknown"

    # -- language spellings -------------------------------------------------
    def cpp(self) -> str:
        k = self.kind
        if k == "scalar":
            return SCALAR_MAP["cpp"][self.canonical]
        if k == "vector":
            return f"std::vector<{SCALAR_MAP['cpp'][self.base]}>"
        if k == "matrix":
            return f"std::vector<std::vector<{SCALAR_MAP['cpp'][self.base]}>>"
        if k in ("listnode", "treenode"):
            return f"{self.canonical}*"
        return "void"

    def java(self) -> str:
        k = self.kind
        if k == "scalar":
            return SCALAR_MAP["java"][self.canonical]
        if k in ("vector", "matrix"):
            return self.base + "[]" * self.depth
        if k in ("listnode", "treenode"):
            return self.canonical
        return "void"

    def c(self) -> str:
        k = self.kind
        if k == "scalar":
            return SCALAR_MAP["c"][self.canonical]
        if k in ("vector", "matrix"):
            return SCALAR_MAP["c"][self.base] + "*"
        if k in ("listnode", "treenode"):
            return f"{self.canonical}*"
        return "void"

    @property
    def scalar_kind(self) -> str:
        """Element type of a vector or matrix, e.g. ``int`` for ``int[][]``."""
        return SCALAR_MAP["c"].get(self.base, "")

    def c_array_ptr(self) -> str:
        """``int*`` for a vector, ``int**`` for a matrix."""
        k = self.kind
        if k == "vector":
            return SCALAR_MAP["c"][self.base] + "*"
        if k == "matrix":
            return SCALAR_MAP["c"][self.base] + "**"
        return self.c()

    def c_len_params(self, name: str) -> list[str]:
        """Extra C parameters needed to carry array sizes."""
        k = self.kind
        if k == "vector":
            return [f"int {name}_len"]
        if k == "matrix":
            return [f"int {name}_rows", f"int {name}_cols"]
        if k == "string":
            return []
        return []


def spec_list(raw) -> list[TypeSpec]:
    """Normalise a problem's param_spec into TypeSpec objects."""
    return [spec for _, spec in named_spec_list(raw)]


def named_spec_list(raw) -> list[tuple[str | None, TypeSpec]]:
    """Like :func:`spec_list` but keeps the optional parameter names.

    ``param_spec`` entries may be a bare type (``"int[]"``) or an object
    (``{"name": "nums", "type": "int[]"}``).
    """
    if not raw:
        return []
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = [p for p in re.split(r"[,\s]+", raw) if p]
    out: list[tuple[str | None, TypeSpec]] = []
    for item in raw:
        name = None
        if isinstance(item, dict):
            name = item.get("name") or None
            item = item.get("type", "")
        canon = normalize(item)
        if canon:
            out.append((name, TypeSpec(canon)))
    return out


def default_name(index: int, function_name: str = "") -> str:
    if index == 0:
        return "arg"
    return f"arg{index}"



def is_supported(spec: TypeSpec) -> bool:
    return spec.kind != "unknown"


def unsupported(spec: TypeSpec) -> str | None:
    """Return a human-readable reason when a spec cannot be handled."""
    if spec.kind == "unknown":
        return (
            f"Unsupported type '{spec.canonical}'. Use one of: "
            + ", ".join(CANONICAL[:-1])
        )
    return None
