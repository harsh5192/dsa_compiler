"""Python harness.

The user's source is executed in a fresh namespace.  The test-case input is
read from stdin as a JSON array of arguments.  A function-style problem is
solved by the first callable found, in this order:

1. a module-level function named ``function_name``
2. ``Solution()`` / ``Main()`` with a method named ``function_name``
3. a single method on such an instance (``solve`` / ``run`` / ``solution``)
"""

from __future__ import annotations

from . import nodes

PREAMBLE = """
import json as _json
import sys as _sys

def _dsa_read_stdin():
    try:
        return _sys.stdin.read()
    except Exception:
        return ""

def _dsa_build_list(values):
    dummy = ListNode()
    dummy.next = None
    tail = dummy
    for v in values or []:
        node = ListNode(0 if v is None else int(v))
        tail.next = node
        tail = node
    return dummy.next

def _dsa_flatten(node):
    out = []
    guard = 0
    while node is not None and guard < 10 ** 7:
        out.append(node.val)
        node = node.next
        guard += 1
    return out

def _dsa_build_tree(values):
    # Level order, LeetCode style: nulls are placeholders for missing children.
    if not values:
        return None
    made = [None if v is None else TreeNode(int(v)) for v in values]
    root = made[0]
    if root is None:
        return None
    idx = 1
    queue = [root]
    while queue:
        node = queue.pop(0)
        if idx < len(made):
            node.left = made[idx]
            idx += 1
        if idx < len(made):
            node.right = made[idx]
            idx += 1
        for child in (node.left, node.right):
            if child is not None:
                queue.append(child)
    return root

def _dsa_tree_values(node):
    out = []
    if node is None:
        return out
    queue = [node]
    while queue:
        cur = queue.pop(0)
        if cur is None:
            out.append(None)
            continue
        out.append(cur.val)
        queue.append(cur.left)
        queue.append(cur.right)
    while out and out[-1] is None:
        out.pop()
    return out
"""

DRIVER_FUNCTION = r'''

# ---------------------------- generated driver ----------------------------
_FN = {function_name!r}
_RETURN = {return_spec!r}
_raw = _dsa_read_stdin()
_args = []
if _raw.strip():
    try:
        _parsed = _json.loads(_raw)
        _args = list(_parsed) if isinstance(_parsed, list) else [_parsed]
    except Exception as exc:  # malformed test case payload
        _sys.stderr.write("TestCaseError: could not decode input as JSON: %s\n" % exc)
        raise SystemExit(4)

# Rebuild list/tree node arguments when the problem expects them.
{node_adapter}

_callable = None
_namespace = globals()
_fn = _namespace.get(_FN)
if callable(_fn):
    _callable = _fn
else:
    for _cls_name in ("Solution", "Main", "Solution1"):
        _cls = _namespace.get(_cls_name)
        if _cls is None:
            continue
        try:
            _inst = _cls()
        except Exception:
            continue
        for _m in (_FN, "solve", "run", "solution"):
            _cand = getattr(_inst, _m, None)
            if callable(_cand):
                _callable = _cand
                break
        if _callable is not None:
            break
if _callable is None:
    _sys.stderr.write("RuntimeError: no callable named %r found. Define "
                      "def %s(...) or class Solution with method %s.\n" % (_FN, _FN, _FN))
    raise SystemExit(3)

_result = _callable(*_typed)
_LIST_CLS = _namespace.get("ListNode")
_TREE_CLS = _namespace.get("TreeNode")
if _LIST_CLS is not None and isinstance(_result, _LIST_CLS):
    _result = _dsa_flatten(_result)
elif _TREE_CLS is not None and isinstance(_result, _TREE_CLS):
    _result = _dsa_tree_values(_result)
elif _result is None and _RETURN == "ListNode":
    _result = []
_sys.stdout.write(_json.dumps(_result, default=str))
# --------------------------------------------------------------------------
'''

DRIVER_STDIN = r'''

# ---------------------------- generated driver ----------------------------
# stdin/stdout program: the code above already read stdin and wrote stdout.
# --------------------------------------------------------------------------
'''


def render(source: str, problem) -> str:
    function_name = problem.function_name or "solution"
    parts = []
    if problem.execution_mode == "function":
        needs = nodes.needs_nodes(problem.param_spec, problem.return_spec)
        if needs and not nodes.user_defines_nodes(source):
            parts.append(nodes.PYTHON)
    parts.append(PREAMBLE)
    parts.append(source)
    if problem.execution_mode == "function":
        adapter = _node_adapter(problem)
        parts.append(
            DRIVER_FUNCTION.format(
                function_name=function_name,
                return_spec=problem.return_spec or "",
                node_adapter=adapter,
            )
        )
    else:
        parts.append(DRIVER_STDIN)
    return "\n".join(parts)


def _param_specs(problem) -> list:
    from ..typespec import spec_list

    return spec_list(problem.param_spec)


def _node_adapter(problem) -> str:
    """Emit argument conversions for the declared parameters."""
    lines = ["_typed = []", "for _i, _a in enumerate(_args):"]
    specs = _param_specs(problem)
    for index, spec in enumerate(specs):
        if spec.kind == "listnode":
            value = "_dsa_build_list(_a)"
        elif spec.kind == "treenode":
            value = "_dsa_build_tree(_a)"
        else:
            # JSON already hands us lists of lists / lists of scalars.
            value = "_a"
        keyword = "if" if index == 0 else "elif"
        lines.append(f"    {keyword} _i == {index}:")
        lines.append(f"        _typed.append({value})")
    lines.append("    else:")
    lines.append("        _typed.append(_a)")
    return "\n".join(lines)
