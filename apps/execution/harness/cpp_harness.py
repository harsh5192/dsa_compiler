"""C++ harness.

Layout of the generated translation unit::

    #include <bits/stdc++.h>
    <platform ListNode/TreeNode helpers, when needed>
    <user source>
    <json reader + converters + main>

The user writes either a free function or a LeetCode-style ``Solution`` class.
``main`` reads the test-case JSON from stdin, converts each element to the
static type declared in the problem's ``param_spec``, calls the solution and
prints the result as compact JSON on stdout.

Exit codes: 0 ok, 1 runtime error, 3 no callable found, 4 bad test payload.
"""

from __future__ import annotations

import re

from . import nodes

PREAMBLE = """#include <bits/stdc++.h>
using namespace std;
"""

RUNTIME = r'''
// --------------------------- generated runtime ---------------------------
struct JV {
    int t = 0;  // 0 null, 1 bool, 2 int, 3 double, 4 string, 5 array
    bool b = false;
    long long i = 0;
    double d = 0;
    string s;
    vector<JV> a;
};

static const char* JP = nullptr;

static void skipWs() {
    while (*JP == ' ' || *JP == '\n' || *JP == '\t' || *JP == '\r') ++JP;
}

static void appendUtf8(string& out, unsigned int cp) {
    if (cp < 0x80) {
        out += static_cast<char>(cp);
    } else if (cp < 0x800) {
        out += static_cast<char>(0xC0 | (cp >> 6));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
        out += static_cast<char>(0xE0 | (cp >> 12));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    }
}

static string parseString() {
    string out;
    ++JP;  // opening quote
    while (*JP && *JP != '"') {
        if (*JP == '\\') {
            ++JP;
            char c = *JP++;
            switch (c) {
                case 'n': out += '\n'; break;
                case 't': out += '\t'; break;
                case 'r': out += '\r'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case '/': out += '/'; break;
                case '\\': out += '\\'; break;
                case '"': out += '"'; break;
                case 'u': {
                    unsigned int cp = 0;
                    for (int k = 0; k < 4 && *JP; ++k) {
                        char h = *JP++;
                        cp <<= 4;
                        if (h >= '0' && h <= '9') cp |= (h - '0');
                        else if (h >= 'a' && h <= 'f') cp |= (h - 'a' + 10);
                        else if (h >= 'A' && h <= 'F') cp |= (h - 'A' + 10);
                    }
                    appendUtf8(out, cp);
                    break;
                }
                default: out += c;
            }
        } else {
            out += *JP++;
        }
    }
    ++JP;  // closing quote
    return out;
}

static JV parseValue();

static void skipContainer() {
    int depth = 0;
    while (*JP) {
        if (*JP == '{' || *JP == '[') ++depth;
        else if (*JP == '}' || *JP == ']') { --depth; if (depth == 0) { ++JP; return; } }
        ++JP;
    }
}

static JV parseValue() {
    skipWs();
    JV v;
    char c = *JP;
    if (c == '{') { skipContainer(); return v; }
    if (c == '[') {
        v.t = 5;
        ++JP;
        skipWs();
        if (*JP == ']') { ++JP; return v; }
        while (true) {
            v.a.push_back(parseValue());
            skipWs();
            if (*JP == ',') { ++JP; continue; }
            if (*JP == ']') { ++JP; }
            break;
        }
        return v;
    }
    if (c == '"') { v.t = 4; v.s = parseString(); return v; }
    if (strncmp(JP, "true", 4) == 0) { v.t = 1; v.b = true; JP += 4; return v; }
    if (strncmp(JP, "false", 5) == 0) { v.t = 1; v.b = false; JP += 5; return v; }
    if (strncmp(JP, "null", 4) == 0) { v.t = 0; JP += 4; return v; }
    const char* start = JP;
    bool isDouble = false;
    while (*JP && (isdigit(static_cast<unsigned char>(*JP)) || *JP == '-' || *JP == '+' ||
                   *JP == '.' || *JP == 'e' || *JP == 'E')) {
        if (*JP == '.' || *JP == 'e' || *JP == 'E') isDouble = true;
        ++JP;
    }
    string num(start, JP);
    if (num.empty()) { if (*JP) ++JP; return v; }
    if (isDouble) { v.t = 3; v.d = strtod(num.c_str(), nullptr); }
    else { v.t = 2; v.i = strtoll(num.c_str(), nullptr, 10); }
    return v;
}

static long long asInt(const JV& v) {
    if (v.t == 2) return v.i;
    if (v.t == 3) return static_cast<long long>(llround(v.d));
    if (v.t == 1) return v.b ? 1 : 0;
    return 0;
}

static double asDouble(const JV& v) {
    if (v.t == 2) return static_cast<double>(v.i);
    if (v.t == 3) return v.d;
    if (v.t == 1) return v.b ? 1.0 : 0.0;
    return 0.0;
}

static string asString(const JV& v) {
    if (v.t == 4) return v.s;
    if (v.t == 2) return to_string(v.i);
    if (v.t == 3) { char buf[64]; snprintf(buf, sizeof(buf), "%g", v.d); return string(buf); }
    if (v.t == 1) return v.b ? "true" : "false";
    return "";
}

static vector<int> toVecInt(const JV& v) {
    vector<int> out; if (v.t == 5) for (const JV& e : v.a) out.push_back(static_cast<int>(asInt(e)));
    return out;
}
static vector<long long> toVecLong(const JV& v) {
    vector<long long> out; if (v.t == 5) for (const JV& e : v.a) out.push_back(asInt(e));
    return out;
}
static vector<double> toVecDouble(const JV& v) {
    vector<double> out; if (v.t == 5) for (const JV& e : v.a) out.push_back(asDouble(e));
    return out;
}
static vector<string> toVecString(const JV& v) {
    vector<string> out; if (v.t == 5) for (const JV& e : v.a) out.push_back(asString(e));
    return out;
}
static vector<vector<int>> toMatInt(const JV& v) {
    vector<vector<int>> out;
    if (v.t == 5) for (const JV& row : v.a) out.push_back(toVecInt(row));
    return out;
}
static vector<vector<long long>> toMatLong(const JV& v) {
    vector<vector<long long>> out;
    if (v.t == 5) for (const JV& row : v.a) out.push_back(toVecLong(row));
    return out;
}
static vector<vector<double>> toMatDouble(const JV& v) {
    vector<vector<double>> out;
    if (v.t == 5) for (const JV& row : v.a) out.push_back(toVecDouble(row));
    return out;
}
static vector<vector<string>> toMatString(const JV& v) {
    vector<vector<string>> out;
    if (v.t == 5) for (const JV& row : v.a) out.push_back(toVecString(row));
    return out;
}
static string jsonEscape(const string& s) {
    string out;
    for (unsigned char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\t': out += "\\t"; break;
            case '\r': out += "\\r"; break;
            default:
                if (c < 0x20) { char buf[8]; snprintf(buf, sizeof(buf), "\\u%04x", c); out += buf; }
                else out += static_cast<char>(c);
        }
    }
    return out;
}

static void printJV(const JV& v) {
    switch (v.t) {
        case 0: printf("null"); break;
        case 1: printf("%s", v.b ? "true" : "false"); break;
        case 2: printf("%lld", v.i); break;
        case 3: printf("%g", v.d); break;
        case 4: printf("\"%s\"", jsonEscape(v.s).c_str()); break;
        case 5: {
            printf("[");
            for (size_t k = 0; k < v.a.size(); ++k) {
                if (k) printf(",");
                printJV(v.a[k]);
            }
            printf("]");
            break;
        }
        default: printf("null");
    }
}
'''

def _vector_result(cpp_type: str, jv_type: int, jv_field: str) -> str:
    return (
        "{ __out.t = 5; for (const auto& __x : __result) "
        f"{{ JV __e; __e.t = {jv_type}; __e.{jv_field} = __x; __out.a.push_back(__e); }} }}"
    )


def _matrix_result(cpp_type: str, jv_type: int, jv_field: str) -> str:
    return (
        "{ __out.t = 5; for (const auto& __row : __result) "
        "{ JV __r; __r.t = 5; "
        f"for (const auto& __x : __row) {{ JV __e; __e.t = {jv_type}; __e.{jv_field} = __x; __r.a.push_back(__e); }} "
        "__out.a.push_back(__r); } }"
    )


#: canonical type -> expression converting a JV into that C++ value
CONVERTERS = {
    "int": "static_cast<int>(asInt({j}))",
    "long": "asInt({j})",
    "double": "asDouble({j})",
    "bool": "({j}.t == 1 ? {j}.b : asInt({j}) != 0)",
    "string": "asString({j})",
    "int[]": "toVecInt({j})",
    "long[]": "toVecLong({j})",
    "double[]": "toVecDouble({j})",
    "string[]": "toVecString({j})",
    "int[][]": "toMatInt({j})",
    "long[][]": "toMatLong({j})",
    "double[][]": "toMatDouble({j})",
    "string[][]": "toMatString({j})",
    "ListNode": "toList({j})",
    "TreeNode": "toTree({j})",
}

_RESULT_EXPR = {
    "int": "{ __out.t = 2; __out.i = (long long)(__result); }",
    "long": "{ __out.t = 2; __out.i = (long long)(__result); }",
    "double": "{ __out.t = 3; __out.d = (double)(__result); }",
    "bool": "{ __out.t = 1; __out.b = (bool)(__result); }",
    "string": "{ __out.t = 4; __out.s = (__result); }",
    "int[]": _vector_result("int", 2, "i"),
    "long[]": _vector_result("long long", 2, "i"),
    "double[]": _vector_result("double", 3, "d"),
    "string[]": _vector_result("string", 4, "s"),
}


_RESULT_EXPR["int[][]"] = _matrix_result("int", 2, "i")
_RESULT_EXPR["long[][]"] = _matrix_result("long long", 2, "i")
_RESULT_EXPR["double[][]"] = _matrix_result("double", 3, "d")
_RESULT_EXPR["string[][]"] = _matrix_result("string", 4, "s")
NODE_RUNTIME = r'''
static ListNode* toList(const JV& v) {
    if (v.t != 5 || v.a.empty()) return nullptr;
    ListNode* head = nullptr; ListNode* tail = nullptr;
    for (const JV& e : v.a) {
        if (e.t == 0) break;
        ListNode* node = new ListNode(static_cast<int>(asInt(e)));
        if (!head) head = node; else tail->next = node;
        tail = node;
    }
    return head;
}
static TreeNode* toTree(const JV& v) {
    if (v.t != 5 || v.a.empty() || v.a[0].t == 0) return nullptr;
    vector<TreeNode*> made;
    for (const JV& e : v.a) {
        if (e.t == 0) made.push_back(nullptr);
        else made.push_back(new TreeNode(static_cast<int>(asInt(e))));
    }
    size_t idx = 1;
    for (size_t k = 0; k < made.size(); ++k) {
        if (!made[k]) continue;
        if (idx < made.size()) made[k]->left = made[idx++];
        if (idx < made.size()) made[k]->right = made[idx++];
    }
    return made[0];
}

static JV fromList(ListNode* p) {
    JV v; v.t = 5;
    while (p) { JV e; e.t = 2; e.i = p->val; v.a.push_back(e); p = p->next; }
    return v;
}

static JV fromTree(TreeNode* root) {
    JV v;
    if (!root) return v;
    v.t = 5;
    queue<TreeNode*> q; q.push(root);
    while (!q.empty()) {
        TreeNode* n = q.front(); q.pop();
        if (!n) { JV e; e.t = 0; v.a.push_back(e); continue; }
        JV e; e.t = 2; e.i = n->val; v.a.push_back(e);
        q.push(n->left); q.push(n->right);
    }
    while (!v.a.empty() && v.a.back().t == 0) v.a.pop_back();
    return v;
}

'''

_RESULT_EXPR["ListNode"] = "{ __out = fromList(__result); }"
_RESULT_EXPR["TreeNode"] = "{ __out = fromTree(__result); }"

DRIVER = r'''
// ---------------------------- generated driver ----------------------------
int main() {
    string raw((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    JP = raw.c_str();
    vector<JV> args;
    {
        skipWs();
        if (*JP) {
            JV root = parseValue();
            if (root.t == 5) args = root.a;
            else args.push_back(root);
        }
    }
__CONVERSIONS__
__DECLARATIONS__
__CALL__
    return 0;
}
'''

CATCH_BLOCK = """
    catch (const std::exception& __e) {
        fprintf(stderr, "RuntimeError: %s\\n", __e.what());
        return 1;
    } catch (...) {
        fprintf(stderr, "RuntimeError: unknown exception\\n");
        return 1;
    }
"""


def _call_expression(source: str, function_name: str, call_args: list[str]) -> str:
    """Free function vs Solution method, decided from the user's source."""
    arglist = ", ".join(call_args)
    escaped = re.escape(function_name)
    if re.search(r"\b(class|struct)\s+Solution\b", source):
        if re.search(r"\bstatic\b[^;{}]*\b" + escaped + r"\s*\(", source):
            return f"Solution::{function_name}({arglist})"
        return f"Solution().{function_name}({arglist})"
    if re.search(r"\b" + escaped + r"\s*\(", source):
        return f"{function_name}({arglist})"
    return f"{function_name}({arglist})"


def render(source: str, problem) -> str:
    from ..typespec import TypeSpec, spec_list, unsupported

    function_name = problem.function_name or "solution"
    params = spec_list(problem.param_spec)
    ret = TypeSpec(problem.return_spec) if problem.return_spec else TypeSpec("void")

    unsupported_reasons = [u for u in (unsupported(p) for p in params) if u]
    if ret.canonical and ret.kind == "unknown":
        unsupported_reasons.append(unsupported(ret))
    if unsupported_reasons:
        raise ValueError("; ".join(unsupported_reasons))

    parts = [PREAMBLE]
    if nodes.needs_nodes(problem.param_spec, problem.return_spec):
        if not nodes.user_defines_nodes(source):
            parts.append(nodes.CPP)
    # RUNTIME defines JV/asInt/printJV, so it has to come before the node
    # converters and the user source that use them.
    parts.append(RUNTIME)
    if nodes.needs_nodes(problem.param_spec, problem.return_spec):
        parts.append(NODE_RUNTIME)
    parts.append(source)

    if problem.execution_mode != "function":
        # stdin/stdout program: the user's code owns main().
        return "\n".join(parts)

    conversions, declarations, call_args = [], [], []
    for index, spec in enumerate(params):
        jv = f"__j{index}"
        conversions.append(
            f"    JV {jv} = ({index} < (int)args.size()) ? args[{index}] : JV();"
        )
        declarations.append(
            f"    {spec.cpp()} a{index} = {CONVERTERS[spec.canonical].format(j=jv)};"
        )
        call_args.append(f"a{index}")

    expression = _call_expression(source, function_name, call_args)
    result = None
    if ret.kind == "void":
        call = f"""    try {{
        {expression};
    }}{CATCH_BLOCK}"""
        result = ""
    else:
        result_expr = _RESULT_EXPR.get(ret.canonical)
        if result_expr is None:
            raise ValueError(f"Unsupported return type for C++: {ret.canonical}")
        call = f"""    try {{
        auto __result = {expression};
        JV __out;
        {result_expr}
        printJV(__out);
    }}{CATCH_BLOCK}"""

    driver = (
        DRIVER.replace("__CONVERSIONS__", "\n".join(conversions))
        .replace("__DECLARATIONS__", "\n".join(declarations))
        .replace("__CALL__", call)
    )
    parts.append(driver)
    return "\n".join(parts)
