"""Starter-code generation.

Every problem declares an ordered ``param_spec`` and a ``return_spec``.  From
those, a LeetCode-shaped skeleton can be produced for any supported language, so
imported problems are immediately solvable without hand-writing five templates.

Existing ``ProblemStarterCode`` rows always win; this module is only the
fallback used when a problem has no stored starter for a language.
"""

from __future__ import annotations

from .typespec import TypeSpec, default_name, named_spec_list

PY_TYPES = {
    "int": "int",
    "long": "int",
    "double": "float",
    "bool": "bool",
    "string": "str",
    "int[]": "List[int]",
    "long[]": "List[int]",
    "double[]": "List[float]",
    "string[]": "List[str]",
    "int[][]": "List[List[int]]",
    "long[][]": "List[List[int]]",
    "double[][]": "List[List[float]]",
    "string[][]": "List[List[str]]",
    "ListNode": "Optional[ListNode]",
    "TreeNode": "Optional[TreeNode]",
}

JS_TYPES = {
    "int": "number",
    "long": "number",
    "double": "number",
    "bool": "boolean",
    "string": "string",
    "int[]": "number[]",
    "long[]": "number[]",
    "double[]": "number[]",
    "string[]": "string[]",
    "int[][]": "number[][]",
    "long[][]": "number[][]",
    "double[][]": "number[][]",
    "string[][]": "string[][]",
    "ListNode": "ListNode | null",
    "TreeNode": "TreeNode | null",
}

JS_RETURNS = {
    "int": "number",
    "long": "number",
    "double": "number",
    "bool": "boolean",
    "string": "string",
    "int[]": "number[]",
    "long[]": "number[]",
    "double[]": "number[]",
    "string[]": "string[]",
    "int[][]": "number[][]",
    "long[][]": "number[][]",
    "double[][]": "number[][]",
    "string[][]": "string[][]",
    "ListNode": "ListNode | null",
    "TreeNode": "TreeNode | null",
}

PLACEHOLDER_VALUES = {
    "int": "0",
    "long": "0",
    "double": "0.0",
    "bool": "False",
    "string": '""',
    "int[]": "[]",
    "long[]": "[]",
    "double[]": "[]",
    "string[]": "[]",
    "int[][]": "[]",
    "long[][]": "[]",
    "double[][]": "[]",
    "string[][]": "[]",
    "ListNode": "None",
    "TreeNode": "None",
}

JAVA_PLACEHOLDERS = {
    "int[]": "new int[0]",
    "long[]": "new long[0]",
    "double[]": "new double[0]",
    "string[]": "new String[0]",
    "int[][]": "new int[0][0]",
    "bool": "false",
    "string": "",
    "int": "0",
    "long": "0L",
    "double": "0.0",
    "ListNode": "null",
    "TreeNode": "null",
}

C_PLACEHOLDERS = {
    "int": "0",
    "long": "0LL",
    "double": "0.0",
    "bool": "0",
    "string": '""',
    "int[]": "NULL",
    "long[]": "NULL",
    "double[]": "NULL",
    "string[]": "NULL",
    "ListNode": "NULL",
    "TreeNode": "NULL",
}


def generate(problem, language) -> str:
    """Return starter code for ``language`` derived from the problem spec."""
    function_name = problem.function_name or "solution"
    named = [
        (name or default_name(index), spec)
        for index, (name, spec) in enumerate(named_spec_list(problem.param_spec))
    ]
    ret = TypeSpec(problem.return_spec) if problem.return_spec else TypeSpec("void")
    generator = {
        "python": _python,
        "javascript": _javascript,
        "cpp": _cpp,
        "java": _java,
        "c": _c,
    }.get(language.slug)
    if generator is None:
        return f"# Write your {language.name} solution for {problem.title}.\n"
    return generator(function_name, named, ret)


def _python(function_name, params, ret) -> str:
    needs_list = any(p.kind in ("vector", "matrix") for _, p in params) or ret.kind in ("vector", "matrix")
    needs_optional = any(
        p.canonical in ("ListNode", "TreeNode") for _, p in params
    ) or ret.canonical in ("ListNode", "TreeNode")
    header = []
    if needs_list and needs_optional:
        header.append("from typing import List, Optional")
    elif needs_list:
        header.append("from typing import List")
    elif needs_optional:
        header.append("from typing import Optional")
    args = ", ".join(
        f"{name}: {PY_TYPES.get(p.canonical, 'object')}" for name, p in params
    )
    if ret.kind == "void":
        body = "        pass"
        signature = f"    def {function_name}({args}) -> None:"
    else:
        body = f"        {PLACEHOLDER_VALUES.get(ret.canonical, 'None')}"
        signature = f"    def {function_name}({args}) -> {PY_TYPES.get(ret.canonical, 'object')}:"
    lines = header + ["", "", "class Solution:", signature, body, ""]
    return "\n".join(lines)


def _javascript(function_name, params, ret) -> str:
    doc = [f" * @param {{{JS_TYPES.get(p.canonical, 'any')}}} {name}" for name, p in params]
    if ret.kind != "void":
        doc.append(f" * @return {{{JS_RETURNS.get(ret.canonical, 'any')}}}")
    args = ", ".join(name for name, _ in params)
    lines = ["/**"]
    lines.extend(doc)
    lines.append(" */")
    if ret.kind == "void":
        return "\n".join(lines + [f"function {function_name}({args}) {{", "  ", "}", ""])
    placeholder = {
        "int": "0",
        "long": "0",
        "double": "0.0",
        "bool": "false",
        "string": '""',
        "int[]": "[]",
        "long[]": "[]",
        "double[]": "[]",
        "string[]": "[]",
        "int[][]": "[]",
        "ListNode": "null",
        "TreeNode": "null",
    }.get(ret.canonical, "null")
    return "\n".join(
        lines
        + [
            f"function {function_name}({args}) {{",
            f"  return {placeholder};",
            "}",
            "",
        ]
    )


def _cpp(function_name, params, ret) -> str:
    args = []
    for name, spec in params:
        if spec.kind == "vector":
            args.append(f"{spec.cpp()}& {name}")
        else:
            args.append(f"{spec.cpp()} {name}")
    if ret.kind == "void":
        return "\n".join(
            [
                "#include <bits/stdc++.h>",
                "using namespace std;",
                "",
                "class Solution {",
                "public:",
                f"    void {function_name}({', '.join(args)}) {{",
                "        ",
                "    }",
                "};",
                "",
            ]
        )
    placeholder = {
        "int": "{}",
        "long": "{}",
        "double": "{}",
        "bool": "false",
        "string": '""',
        "int[]": "{}",
        "long[]": "{}",
        "double[]": "{}",
        "string[]": "{}",
        "int[][]": "{}",
        "ListNode": "nullptr",
        "TreeNode": "nullptr",
    }.get(ret.canonical, "{}")
    return "\n".join(
        [
            "#include <bits/stdc++.h>",
            "using namespace std;",
            "",
            "class Solution {",
            "public:",
            f"    {ret.cpp()} {function_name}({', '.join(args)}) {{",
            f"        return {placeholder};",
            "    }",
            "};",
            "",
        ]
    )


def _java(function_name, params, ret) -> str:
    args = ", ".join(f"{p.java()} {name}" for name, p in params)
    if ret.kind == "void":
        return "\n".join(
            [
                "class Solution {",
                f"    public void {function_name}({args}) {{",
                "        ",
                "    }",
                "}",
                "",
            ]
        )
    placeholder = JAVA_PLACEHOLDERS.get(ret.canonical, "null")
    return "\n".join(
        [
            "class Solution {",
            f"    public {ret.java()} {function_name}({args}) {{",
            f"        return {placeholder};",
            "    }",
            "}",
            "",
        ]
    )


def _c(function_name, params, ret) -> str:
    args, decls = [], []
    for name, spec in params:
        # Arrays are pointers in C, and a 2D array is a pointer to pointers.
        declared = spec.c_array_ptr() if spec.kind in ("vector", "matrix") else spec.c()
        args.append(f"{declared} {name}")
        decls.append(f"    {declared} {name};")
        for extra in spec.c_len_params(name):
            args.append(extra)
            decls.append(f"    {extra};")

    hint = {
        "vector": (
            f"/* Return a malloc'd array and set the size in {function_name}_len. */\n"
        ),
        "matrix": (
            "/* Return a 2D array, set the row count in "
            f"{function_name}_rows and end every row so the platform can print "
            "it: NULL for char* rows, DSA_ROW_END_INT / DSA_ROW_END_LONG / "
            "DSA_ROW_END_DOUBLE otherwise. */\n"
        ),
        "void": "",
    }.get(ret.kind, "")

    if ret.kind == "void":
        body = "    (void)arg0;"
    elif ret.kind == "vector":
        body = f"    {function_name}_len = 0;\n    return NULL;"
    elif ret.kind == "matrix":
        body = f"    {function_name}_rows = 0;\n    return NULL;"
    else:
        body = f"    return {C_PLACEHOLDERS.get(ret.canonical, '0')};"

    declared_ret = ret.c_array_ptr() if ret.kind in ("vector", "matrix") else ret.c()
    return "\n".join(
        [
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "",
            hint.rstrip(),
            f"{declared_ret} {function_name}({', '.join(args)}) {{",
            *(decls if ret.kind == "void" else []),
            body,
            "}",
            "",
        ]
    )
