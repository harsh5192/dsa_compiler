"""C harness.

C has no return-type introspection, so the platform uses one explicit
convention, which the generated starter code documents:

* arrays are passed as ``T*`` followed by a length argument ``<name>_len``
* a vector/string/nodelist result is written into a caller-provided buffer and
  the function returns the number of elements written
* scalars and pointers are returned directly

stdin carries the test-case JSON; stdout receives compact JSON.
"""

from __future__ import annotations

import re

from . import nodes

PREAMBLE = """#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
"""

RUNTIME = r'''
/* --------------------------- generated runtime --------------------------- */
typedef enum { J_NULL, J_BOOL, J_INT, J_DBL, J_STR, J_ARR } JKind;

typedef struct JV {
    JKind kind;
    long long i;
    double d;
    char *s;
    struct JV *items;
    int count;
} JV;

static const char *JP = NULL;
static char *JPEOF = NULL;

static void jv_free(JV *v) {
    if (!v) return;
    if (v->kind == J_ARR) {
        for (int k = 0; k < v->count; k++) jv_free(&v->items[k]);
        free(v->items);
    }
    if (v->kind == J_STR) free(v->s);
    v->items = NULL;
    v->s = NULL;
}

static void skip_ws(void) {
    while (*JP == ' ' || *JP == '\n' || *JP == '\t' || *JP == '\r') JP++;
}

static char *parse_c_string(void) {
    JP++;  /* opening quote */
    size_t cap = 32, len = 0;
    char *out = (char *) malloc(cap);
    while (*JP && *JP != '"') {
        char c = *JP;
        if (c == '\\') {
            JP++;
            char e = *JP++;
            switch (e) {
                case 'n': c = '\n'; break;
                case 't': c = '\t'; break;
                case 'r': c = '\r'; break;
                case 'b': c = '\b'; break;
                case 'f': c = '\f'; break;
                case 'u': {
                    /* naive: keep the raw escape target as a placeholder char */
                    for (int k = 0; k < 4 && *JP; k++) JP++;
                    c = '?';
                    break;
                }
                default: c = e;
            }
        } else {
            JP++;
        }
        if (len + 1 >= cap) { cap *= 2; out = (char *) realloc(out, cap); }
        out[len++] = c;
    }
    JP++;  /* closing quote */
    out[len] = '\0';
    return out;
}

static JV parse_value(void);

static void skip_container(void) {
    int depth = 0;
    while (*JP) {
        if (*JP == '{' || *JP == '[') depth++;
        else if (*JP == '}' || *JP == ']') { depth--; if (depth == 0) { JP++; return; } }
        JP++;
    }
}

static JV parse_value(void) {
    JV v;
    memset(&v, 0, sizeof(v));
    v.kind = J_NULL;
    skip_ws();
    char c = *JP;
    if (c == '{') { skip_container(); return v; }
    if (c == '[') {
        v.kind = J_ARR;
        JP++;
        skip_ws();
        if (*JP == ']') { JP++; return v; }
        int cap = 4;
        v.items = (JV *) calloc((size_t) cap, sizeof(JV));
        while (1) {
            if (v.count >= cap) { cap *= 2; v.items = (JV *) realloc(v.items, (size_t) cap * sizeof(JV)); }
            v.items[v.count++] = parse_value();
            skip_ws();
            if (*JP == ',') { JP++; continue; }
            if (*JP == ']') JP++;
            break;
        }
        return v;
    }
    if (c == '"') { v.kind = J_STR; v.s = parse_c_string(); return v; }
    if (strncmp(JP, "true", 4) == 0) { v.kind = J_BOOL; v.i = 1; JP += 4; return v; }
    if (strncmp(JP, "false", 5) == 0) { v.kind = J_BOOL; v.i = 0; JP += 5; return v; }
    if (strncmp(JP, "null", 4) == 0) { v.kind = J_NULL; JP += 4; return v; }
    const char *start = JP;
    int is_double = 0;
    while (*JP && (isdigit((unsigned char) *JP) || *JP == '-' || *JP == '+' ||
                   *JP == '.' || *JP == 'e' || *JP == 'E')) {
        if (*JP == '.' || *JP == 'e' || *JP == 'E') is_double = 1;
        JP++;
    }
    if (JP == start) return v;
    if (is_double) { v.kind = J_DBL; v.d = strtod(start, NULL); }
    else { v.kind = J_INT; v.i = strtoll(start, NULL, 10); }
    return v;
}

static long long as_int(JV v) {
    if (v.kind == J_INT) return v.i;
    if (v.kind == J_DBL) return (long long) llround(v.d);
    if (v.kind == J_BOOL) return v.i;
    return 0;
}

static double as_double(JV v) {
    if (v.kind == J_INT) return (double) v.i;
    if (v.kind == J_DBL) return v.d;
    if (v.kind == J_BOOL) return (double) v.i;
    return 0.0;
}

/* strdup is POSIX, not C11, so -std=c11 hides its prototype. */
static char *dsa_strdup(const char *src) {
    if (!src) return NULL;
    size_t n = strlen(src) + 1;
    char *out = (char *) malloc(n);
    if (out) memcpy(out, src, n);
    return out;
}
/* Let submitted code call strdup() without pulling in POSIX headers. */
#define strdup dsa_strdup

/* Row terminator for two dimensional results, so rows may have different
   lengths. Terminate every returned row with DSA_ROW_END and publish only the
   row count. */
#include <limits.h>
#define DSA_ROW_END_INT INT_MIN
#define DSA_ROW_END_LONG LLONG_MIN
#define DSA_ROW_END_DOUBLE (-1.0e308)

static char *as_string(JV v) {
    if (v.kind == J_STR) return v.s;
    if (v.kind == J_INT) { char buf[32]; snprintf(buf, sizeof(buf), "%lld", v.i); return dsa_strdup(buf); }
    if (v.kind == J_BOOL) return dsa_strdup(v.i ? "true" : "false");
    if (v.kind == J_DBL) { char buf[64]; snprintf(buf, sizeof(buf), "%g", v.d); return dsa_strdup(buf); }
    return dsa_strdup("");
}

static int jv_count(JV v) { return v.kind == J_ARR ? v.count : 0; }

static void print_json_string(const char *s) {
    putchar('"');
    for (const char *p = s ? s : ""; *p; p++) {
        if (*p == '"') fputs("\\\"", stdout);
        else if (*p == '\\') fputs("\\\\", stdout);
        else if (*p == '\n') fputs("\\n", stdout);
        else if (*p == '\t') fputs("\\t", stdout);
        else if (*p == '\r') fputs("\\r", stdout);
        else if ((unsigned char) *p < 0x20) printf("\\u%04x", (unsigned char) *p);
        else putchar(*p);
    }
    putchar('"');
}
'''

PARAM_CONVERTERS = {
    "int": "    int a{i} = (int) as_int(args[{i}]);",
    "long": "    long long a{i} = as_int(args[{i}]);",
    "double": "    double a{i} = as_double(args[{i}]);",
    "bool": "    int a{i} = (args[{i}].kind == J_BOOL) ? (int) args[{i}].i : (as_int(args[{i}]) != 0);",
    "string": "    char *a{i} = as_string(args[{i}]);",
    "int[]": "    int a{i}_len = jv_count(args[{i}]);\n    int *a{i} = (int *) malloc(sizeof(int) * (size_t)(a{i}_len > 0 ? a{i}_len : 1));\n    for (int k = 0; k < a{i}_len; k++) a{i}[k] = (int) as_int(args[{i}].items[k]);",
    "long[]": "    int a{i}_len = jv_count(args[{i}]);\n    long long *a{i} = (long long *) malloc(sizeof(long long) * (size_t)(a{i}_len > 0 ? a{i}_len : 1));\n    for (int k = 0; k < a{i}_len; k++) a{i}[k] = as_int(args[{i}].items[k]);",
    "double[]": "    int a{i}_len = jv_count(args[{i}]);\n    double *a{i} = (double *) malloc(sizeof(double) * (size_t)(a{i}_len > 0 ? a{i}_len : 1));\n    for (int k = 0; k < a{i}_len; k++) a{i}[k] = as_double(args[{i}].items[k]);",
    "string[]": "    int a{i}_len = jv_count(args[{i}]);\n    char **a{i} = (char **) malloc(sizeof(char *) * (size_t)(a{i}_len > 0 ? a{i}_len : 1));\n    for (int k = 0; k < a{i}_len; k++) a{i}[k] = as_string(args[{i}].items[k]);",
    "int[][]": "    int a{i}_rows = jv_count(args[{i}]);\n    int a{i}_cols = a{i}_rows > 0 ? jv_count(args[{i}].items[0]) : 0;\n    int **a{i} = (int **) malloc(sizeof(int *) * (size_t)(a{i}_rows > 0 ? a{i}_rows : 1));\n    for (int r = 0; r < a{i}_rows; r++) {\n        a{i}[r] = (int *) malloc(sizeof(int) * (size_t)(a{i}_cols > 0 ? a{i}_cols : 1));\n        for (int c = 0; c < a{i}_cols; c++) a{i}[r][c] = (int) as_int(args[{i}].items[r].items[c]);\n    }",
    "long[][]": "    int a{i}_rows = jv_count(args[{i}]);\n    int a{i}_cols = a{i}_rows > 0 ? jv_count(args[{i}].items[0]) : 0;\n    long long **a{i} = (long long **) malloc(sizeof(long long *) * (size_t)(a{i}_rows > 0 ? a{i}_rows : 1));\n    for (int r = 0; r < a{i}_rows; r++) {\n        a{i}[r] = (long long *) malloc(sizeof(long long) * (size_t)(a{i}_cols > 0 ? a{i}_cols : 1));\n        for (int c = 0; c < a{i}_cols; c++) a{i}[r][c] = (long long) as_int(args[{i}].items[r].items[c]);\n    }",
    "double[][]": "    int a{i}_rows = jv_count(args[{i}]);\n    int a{i}_cols = a{i}_rows > 0 ? jv_count(args[{i}].items[0]) : 0;\n    double **a{i} = (double **) malloc(sizeof(double *) * (size_t)(a{i}_rows > 0 ? a{i}_rows : 1));\n    for (int r = 0; r < a{i}_rows; r++) {\n        a{i}[r] = (double *) malloc(sizeof(double) * (size_t)(a{i}_cols > 0 ? a{i}_cols : 1));\n        for (int c = 0; c < a{i}_cols; c++) a{i}[r][c] = (double) as_double(args[{i}].items[r].items[c]);\n    }",
    "string[][]": "    int a{i}_rows = jv_count(args[{i}]);\n    int a{i}_cols = a{i}_rows > 0 ? jv_count(args[{i}].items[0]) : 0;\n    char ***a{i} = (char ***) malloc(sizeof(char *) * (size_t)(a{i}_rows > 0 ? a{i}_rows : 1));\n    for (int r = 0; r < a{i}_rows; r++) {\n        a{i}[r] = (char ** *) malloc(sizeof(char) * (size_t)(a{i}_cols > 0 ? a{i}_cols : 1));\n        for (int c = 0; c < a{i}_cols; c++) a{i}[r][c] = (char) as_string(args[{i}].items[r].items[c]);\n    }",
    "ListNode": "    ListNode *a{i} = (ListNode *) NULL;\n    {\n        int n = jv_count(args[{i}]);\n        ListNode *head = NULL, *tail = NULL;\n        for (int k = 0; k < n; k++) {\n            if (args[{i}].items[k].kind == J_NULL) break;\n            ListNode *node = (ListNode *) malloc(sizeof(ListNode));\n            node->val = (int) as_int(args[{i}].items[k]);\n            node->next = NULL;\n            if (!head) head = node; else tail->next = node;\n            tail = node;\n        }\n        a{i} = head;\n    }",
    "TreeNode": "    TreeNode *a{i} = (TreeNode *) NULL;\n    {\n        int n = jv_count(args[{i}]);\n        if (n > 0 && args[{i}].items[0].kind != J_NULL) {\n            TreeNode **made = (TreeNode **) calloc((size_t) n, sizeof(TreeNode *));\n            for (int k = 0; k < n; k++) {\n                if (args[{i}].items[k].kind == J_NULL) continue;\n                made[k] = (TreeNode *) malloc(sizeof(TreeNode));\n                made[k]->val = (int) as_int(args[{i}].items[k]);\n                made[k]->left = NULL;\n                made[k]->right = NULL;\n            }\n            int idx = 1;\n            for (int k = 0; k < n; k++) {\n                if (!made[k]) continue;\n                if (idx < n) made[k]->left = made[idx++];\n                if (idx < n) made[k]->right = made[idx++];\n            }\n            a{i} = made[0];\n        }\n    }",
}

DRIVER = r'''
/* ---------------------------- generated driver ---------------------------- */
#define OUT_CAP 65536

int main(void) {
    size_t cap = 8192, len = 0;
    char *raw = (char *) malloc(cap);
    int ch;
    while ((ch = getchar()) != EOF) {
        if (len + 1 >= cap) { cap *= 2; raw = (char *) realloc(raw, cap); }
        raw[len++] = (char) ch;
    }
    raw[len] = '\0';

    JP = raw;
    JV root = parse_value();
    int argc = 1;
    JV *args = (JV *) calloc((size_t) argc, sizeof(JV));
    if (root.kind == J_ARR) {
        argc = root.count;
        args = (JV *) calloc((size_t) (argc > 0 ? argc : 1), sizeof(JV));
        for (int i = 0; i < argc; i++) args[i] = root.items[i];
    } else {
        args[0] = root;
    }
    while (argc < __PARAM_COUNT__) {
        JV blank;
        memset(&blank, 0, sizeof(blank));
        blank.kind = J_NULL;
        args = (JV *) realloc(args, sizeof(JV) * (size_t) (argc + 1));
        args[argc++] = blank;
    }

__CONVERSIONS__
__CALL__
    return 0;
}
'''


def render(source: str, problem) -> str:
    from ..typespec import TypeSpec, spec_list, unsupported

    function_name = problem.function_name or "solution"
    params = spec_list(problem.param_spec)
    ret = TypeSpec(problem.return_spec) if problem.return_spec else TypeSpec("void")

    reasons = [u for u in (unsupported(p) for p in params) if u]
    if ret.kind == "unknown":
        reasons.append(unsupported(ret))
    if reasons:
        raise ValueError("; ".join(reasons))

    if ret.kind in ("vector", "matrix"):
        # C has no way to return "array + length", so the platform declares
        # length globals before the user's code and reads them back in main.
        globals_decl = _length_globals(function_name, ret)
    else:
        globals_decl = ""

    parts = [PREAMBLE, globals_decl]
    if nodes.needs_nodes(problem.param_spec, problem.return_spec) and not nodes.user_defines_nodes(source):
        parts.append(nodes.C)
    # RUNTIME provides the JSON helpers, the strdup shim and the node helpers that
    # submitted code may call, so it has to precede the user source.
    parts.append(RUNTIME)
    parts.append(source)

    if problem.execution_mode != "function":
        return "\n".join(parts)

    conversions = []
    for index, spec in enumerate(params):
        template = PARAM_CONVERTERS.get(spec.canonical)
        if template is None:
            raise ValueError(f"Unsupported C parameter type: {spec.canonical}")
        conversions.append(template.replace("{i}", str(index)))

    # C has no arrays, so every array argument is followed by its length (or
    # row/column count) straight after the pointer.
    call_args = []
    for index, spec in enumerate(params):
        call_args.append(f"a{index}")
        if spec.kind == "vector":
            call_args.append(f"a{index}_len")
        elif spec.kind == "matrix":
            call_args.extend([f"a{index}_rows", f"a{index}_cols"])

    call = _build_call(source, function_name, call_args, ret)
    driver = (
        DRIVER.replace("__CONVERSIONS__", "\n".join(conversions))
        .replace("__CALL__", call)
        .replace("__PARAM_COUNT__", str(len(params)))
    )
    parts.append(driver)
    return "\n".join(parts)


def _length_globals(function_name: str, ret) -> str:
    lines = [
        "/* --- result size globals provided by the platform --- */"
    ]
    if ret.kind == "vector":
        lines.append(f"int {function_name}_len = 0;")
    else:
        # Matrix rows are terminated individually, so rows may differ in length
        # and only the row count is published.
        lines.append(f"int {function_name}_rows = 0;")
    lines.append("/* --- end result size globals --- */")
    return "\n".join(lines)


_PRINTER = {
    "int[]": 'printf("%d", __v[k])',
    "long[]": 'printf("%lld", __v[k])',
    "double[]": 'printf("%g", __v[k])',
    "string[]": 'print_json_string(__v[k])',
    "int[][]": 'printf("%d", __v[r][c])',
    "long[][]": 'printf("%lld", __v[r][c])',
    "double[][]": 'printf("%g", __v[r][c])',
    "string[][]": 'print_json_string(__v[r][c])',
}


def _build_call(source, function_name, call_args, ret) -> str:
    arglist = ", ".join(call_args)
    escaped = re.escape(function_name)
    if re.search(r"\b(class|struct)\s+Solution\b", source):
        target = f"Solution().{function_name}({arglist})"
    else:
        target = f"{function_name}({arglist})"

    if ret.kind == "void":
        return f"    {target};\n"

    if ret.kind == "vector":
        printer = _PRINTER[ret.canonical]
        return (
            "    {\n"
            f"        {ret.c_array_ptr()} __v = {target};\n"
            "        putchar('[');\n"
            f"        for (int k = 0; k < {function_name}_len; k++)"
            f" {{ if (k) putchar(','); {printer}; }}\n"
            "        putchar(']');\n"
            "    }\n"
        )

    if ret.kind == "matrix" and ret.c() == "char**":
        # Ragged string matrix: rows are NULL terminated, so walk them directly.
        return (
            "    {\n"
            f"        char ***__v = {target};\n"
            "        putchar('[');\n"
            f"        for (int r = 0; r < {function_name}_rows; r++) {{\n"
            "            if (r) putchar(',');\n"
            "            putchar('[');\n"
            "            for (int c = 0; __v[r][c]; c++)"
            " { if (c) putchar(','); print_json_string(__v[r][c]); }\n"
            "            putchar(']');\n"
            "        }\n"
            "        putchar(']');\n"
            "    }\n"
        )

    if ret.kind == "matrix":
        printer = _PRINTER[ret.canonical]
        # Key on the canonical element type: scalar_kind reports the C spelling
        # ("long long"), while the macros follow the canonical name ("long").
        terminator = {
            "int": "DSA_ROW_END_INT",
            "long": "DSA_ROW_END_LONG",
            "double": "DSA_ROW_END_DOUBLE",
        }.get(ret.base, "")
        if not terminator:
            raise ValueError(
                f"cannot print a C matrix of {ret.canonical}: no row terminator is defined"
            )
        return (
            "    {\n"
            f"        {ret.c_array_ptr()} __v = {target};\n"
            "        putchar('[');\n"
            f"        for (int r = 0; r < {function_name}_rows; r++) {{\n"
            "            if (r) putchar(',');\n"
            "            putchar('[');\n"
            f"            for (int c = 0; __v[r][c] != {terminator}; c++)"
            f" {{ if (c) putchar(','); {printer}; }}\n"
            "            putchar(']');\n"
            "        }\n"
            "        putchar(']');\n"
            "    }\n"
        )

    emit = {
        "int": '    printf("%d\\n", (int)({target}));',
        "long": '    printf("%lld\\n", (long long)({target}));',
        "double": '    printf("%g\\n", (double)({target}));',
        "bool": '    printf("%s\\n", ({target}) ? "true" : "false");',
        "string": '    {{ char *__s = (char *)({target}); print_json_string(__s); putchar(\'\\n\'); }}',
        "ListNode": '    {{ ListNode *__h = ({target}); putchar(\'[\'); for (ListNode *__p = __h; __p; __p = __p->next) {{ if (__p != __h) putchar(\',\'); printf("%d", __p->val); }} putchar(\']\'); putchar(\'\\n\'); }}',
        "TreeNode": '    {{ TreeNode *__r = ({target}); if (!__r) {{ printf("null\\n"); }} else {{ int __qc = 16, __qh = 0, __qt = 0; TreeNode **__q = (TreeNode **) calloc((size_t) __qc, sizeof(TreeNode *)); __q[__qt++] = __r; int __first = 1; while (__qh < __qt) {{ TreeNode *__c = __q[__qh++]; if (!__c) {{ if (!__first) putchar(\',\'); printf("null"); }} else {{ if (!__first) putchar(\',\'); printf("%d", __c->val); if (__qt + 2 > __qc) {{ __qc *= 2; __q = (TreeNode **) realloc(__q, (size_t) __qc * sizeof(TreeNode *)); }} __q[__qt++] = __c->left; __q[__qt++] = __c->right; }} __first = 0; }} putchar(\']\'); putchar(\'\\n\'); }} }}',
    }.get(ret.canonical)
    if emit is None:
        raise ValueError(f"Unsupported C return type: {ret.canonical}")
    return emit.format(target=target) + "\n"
