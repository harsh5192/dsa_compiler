"""Java harness.

Produces two files:

* ``Solution.java`` -- the user's source, untouched.
* ``Main.java``     -- stdin reader, a small JSON parser, argument converters
  and a reflective call into the user's solution.

The callable is resolved by reflection so both styles work::

    class Solution { public int[] twoSum(int[] nums, int target) {...} }
    class TwoSum   { public static int[] twoSum(...) {...} }
"""

from __future__ import annotations

import re

from . import nodes

MAIN = r'''import java.io.*;
import java.lang.reflect.*;
import java.util.*;

// --------------------------- generated runtime ---------------------------
public class Main {

    // --- tiny JSON reader ---------------------------------------------------
    static final class JV {
        static final int NULL = 0, BOOL = 1, INT = 2, DBL = 3, STR = 4, ARR = 5;
        int t = NULL;
        boolean b;
        long i;
        double d;
        String s;
        List<JV> a = new ArrayList<JV>();
    }

    static String raw;
    static int pos;

    static void skipWs() {
        while (pos < raw.length()) {
            char c = raw.charAt(pos);
            if (c == ' ' || c == '\n' || c == '\t' || c == '\r') pos++; else break;
        }
    }

    static String parseString() {
        StringBuilder sb = new StringBuilder();
        pos++;  // opening quote
        while (pos < raw.length() && raw.charAt(pos) != '"') {
            char c = raw.charAt(pos);
            if (c == '\\' && pos + 1 < raw.length()) {
                pos++;
                char e = raw.charAt(pos);
                switch (e) {
                    case 'n': sb.append('\n'); break;
                    case 't': sb.append('\t'); break;
                    case 'r': sb.append('\r'); break;
                    case 'b': sb.append('\b'); break;
                    case 'f': sb.append('\f'); break;
                    case 'u':
                        if (pos + 4 < raw.length()) {
                            sb.append((char) Integer.parseInt(raw.substring(pos + 1, pos + 5), 16));
                            pos += 4;
                        }
                        break;
                    default: sb.append(e);
                }
            } else {
                sb.append(c);
            }
            pos++;
        }
        pos++;  // closing quote
        return sb.toString();
    }

    static JV parseValue() {
        skipWs();
        JV v = new JV();
        if (pos >= raw.length()) return v;
        char c = raw.charAt(pos);
        if (c == '{') {
            int depth = 0;
            while (pos < raw.length()) {
                char k = raw.charAt(pos);
                if (k == '{' || k == '[') depth++;
                else if (k == '}' || k == ']') { depth--; pos++; if (depth == 0) return v; continue; }
                pos++;
            }
            return v;
        }
        if (c == '[') {
            v.t = JV.ARR;
            pos++;
            skipWs();
            if (pos < raw.length() && raw.charAt(pos) == ']') { pos++; return v; }
            while (true) {
                v.a.add(parseValue());
                skipWs();
                if (pos < raw.length() && raw.charAt(pos) == ',') { pos++; continue; }
                if (pos < raw.length() && raw.charAt(pos) == ']') pos++;
                break;
            }
            return v;
        }
        if (c == '"') { v.t = JV.STR; v.s = parseString(); return v; }
        if (raw.startsWith("true", pos)) { v.t = JV.BOOL; v.b = true; pos += 4; return v; }
        if (raw.startsWith("false", pos)) { v.t = JV.BOOL; v.b = false; pos += 5; return v; }
        if (raw.startsWith("null", pos)) { v.t = JV.NULL; pos += 4; return v; }
        int start = pos;
        boolean isDouble = false;
        while (pos < raw.length()) {
            char k = raw.charAt(pos);
            if (Character.isDigit(k) || k == '-' || k == '+' || k == '.'
                    || k == 'e' || k == 'E') {
                if (k == '.' || k == 'e' || k == 'E') isDouble = true;
                pos++;
            } else break;
        }
        String num = raw.substring(start, pos);
        if (num.isEmpty()) { if (pos < raw.length()) pos++; return v; }
        try {
            if (isDouble) { v.t = JV.DBL; v.d = Double.parseDouble(num); }
            else { v.t = JV.INT; v.i = Long.parseLong(num); }
        } catch (NumberFormatException e) { /* leave as null */ }
        return v;
    }

    // --- converters ---------------------------------------------------------
    static long asLong(JV v) {
        if (v.t == JV.INT) return v.i;
        if (v.t == JV.DBL) return Math.round(v.d);
        if (v.t == JV.BOOL) return v.b ? 1 : 0;
        return 0;
    }

    static double asDouble(JV v) {
        if (v.t == JV.INT) return (double) v.i;
        if (v.t == JV.DBL) return v.d;
        if (v.t == JV.BOOL) return v.b ? 1.0 : 0.0;
        return 0.0;
    }

    static String asString(JV v) {
        if (v.t == JV.STR) return v.s;
        if (v.t == JV.INT) return Long.toString(v.i);
        if (v.t == JV.DBL) return Double.toString(v.d);
        if (v.t == JV.BOOL) return v.b ? "true" : "false";
        return "";
    }

    static int[] toIntArray(JV v) {
        if (v.t != JV.ARR) return new int[0];
        int[] out = new int[v.a.size()];
        for (int k = 0; k < out.length; k++) out[k] = (int) asLong(v.a.get(k));
        return out;
    }

    static long[] toLongArray(JV v) {
        if (v.t != JV.ARR) return new long[0];
        long[] out = new long[v.a.size()];
        for (int k = 0; k < out.length; k++) out[k] = asLong(v.a.get(k));
        return out;
    }

    static double[] toDoubleArray(JV v) {
        if (v.t != JV.ARR) return new double[0];
        double[] out = new double[v.a.size()];
        for (int k = 0; k < out.length; k++) out[k] = asDouble(v.a.get(k));
        return out;
    }

    static String[] toStringArray(JV v) {
        if (v.t != JV.ARR) return new String[0];
        String[] out = new String[v.a.size()];
        for (int k = 0; k < out.length; k++) out[k] = asString(v.a.get(k));
        return out;
    }

    static int[][] toIntMatrix(JV v) {
        if (v.t != JV.ARR) return new int[0][];
        int[][] out = new int[v.a.size()][];
        for (int k = 0; k < out.length; k++) out[k] = toIntArray(v.a.get(k));
        return out;
    }

    static Object toList(JV v) throws Exception {
        if (v.t != JV.ARR || v.a.isEmpty()) return null;
        Class<?> cls = Class.forName("ListNode");
        Constructor<?> ctor = cls.getDeclaredConstructor(int.class);
        ctor.setAccessible(true);
        Field valField = cls.getDeclaredField("val");
        Field nextField = cls.getDeclaredField("next");
        valField.setAccessible(true);
        nextField.setAccessible(true);
        Object head = null, prev = null;
        for (JV e : v.a) {
            if (e.t == JV.NULL) break;
            Object node = ctor.newInstance((int) asLong(e));
            if (head == null) head = node; else nextField.set(prev, node);
            prev = node;
        }
        return head;
    }

    static Object toTree(JV v) throws Exception {
        if (v.t != JV.ARR || v.a.isEmpty() || v.a.get(0).t == JV.NULL) return null;
        Class<?> cls = Class.forName("TreeNode");
        Constructor<?> ctor = cls.getDeclaredConstructor(int.class);
        ctor.setAccessible(true);
        Field valField = cls.getDeclaredField("val");
        Field leftField = cls.getDeclaredField("left");
        Field rightField = cls.getDeclaredField("right");
        valField.setAccessible(true);
        leftField.setAccessible(true);
        rightField.setAccessible(true);
        List<JV> items = v.a;
        Object[] made = new Object[items.size()];
        for (int k = 0; k < items.size(); k++) {
            JV e = items.get(k);
            made[k] = e.t == JV.NULL ? null : ctor.newInstance((int) asLong(e));
        }
        int idx = 1;
        for (int k = 0; k < made.length; k++) {
            if (made[k] == null) continue;
            if (idx < made.length) leftField.set(made[k], made[idx++]);
            if (idx < made.length) rightField.set(made[k], made[idx++]);
        }
        return made[0];
    }

    // --- output -------------------------------------------------------------
    static void escape(StringBuilder sb, String s) {
        for (int k = 0; k < s.length(); k++) {
            char c = s.charAt(k);
            if (c == '"') sb.append("\\\"");
            else if (c == '\\') sb.append("\\\\");
            else if (c == '\n') sb.append("\\n");
            else if (c == '\t') sb.append("\\t");
            else if (c == '\r') sb.append("\\r");
            else if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
            else sb.append(c);
        }
    }

    static void writeIntArray(StringBuilder sb, int[] arr) {
        sb.append('[');
        for (int k = 0; k < arr.length; k++) { if (k > 0) sb.append(','); sb.append(arr[k]); }
        sb.append(']');
    }

    static void writeLongArray(StringBuilder sb, long[] arr) {
        sb.append('[');
        for (int k = 0; k < arr.length; k++) { if (k > 0) sb.append(','); sb.append(arr[k]); }
        sb.append(']');
    }

    static void writeDoubleArray(StringBuilder sb, double[] arr) {
        sb.append('[');
        for (int k = 0; k < arr.length; k++) {
            if (k > 0) sb.append(',');
            if (arr[k] == Math.rint(arr[k]) && !Double.isInfinite(arr[k])) {
                sb.append((long) arr[k]);
            } else {
                sb.append(arr[k]);
            }
        }
        sb.append(']');
    }

    static void writeStringArray(StringBuilder sb, String[] arr) {
        sb.append('[');
        for (int k = 0; k < arr.length; k++) {
            if (k > 0) sb.append(',');
            sb.append('"'); escape(sb, arr[k] == null ? "" : arr[k]); sb.append('"');
        }
        sb.append(']');
    }

    static void writeIntMatrix(StringBuilder sb, int[][] m) {
        sb.append('[');
        for (int k = 0; k < m.length; k++) { if (k > 0) sb.append(','); writeIntArray(sb, m[k]); }
        sb.append(']');
    }

    static void writeObject(StringBuilder sb, Object node, boolean isList) {
        if (node == null) { sb.append("null"); return; }
        try {
            if (isList) {
                Field valField = node.getClass().getDeclaredField("val");
                Field nextField = node.getClass().getDeclaredField("next");
                valField.setAccessible(true);
                nextField.setAccessible(true);
                sb.append('[');
                Object cur = node;
                while (cur != null) {
                    sb.append(valField.getInt(cur));
                    cur = nextField.get(cur);
                    if (cur != null) sb.append(',');
                }
                sb.append(']');
            } else {
                Field valField = node.getClass().getDeclaredField("val");
                Field leftField = node.getClass().getDeclaredField("left");
                Field rightField = node.getClass().getDeclaredField("right");
                valField.setAccessible(true);
                leftField.setAccessible(true);
                rightField.setAccessible(true);
                List<Object> out = new ArrayList<Object>();
                Deque<Object> queue = new ArrayDeque<Object>();
                queue.add(node);
                while (!queue.isEmpty()) {
                    Object cur = queue.poll();
                    if (cur == null) { out.add(null); continue; }
                    out.add(valField.getInt(cur));
                    queue.add(leftField.get(cur));
                    queue.add(rightField.get(cur));
                }
                while (!out.isEmpty() && out.get(out.size() - 1) == null) out.remove(out.size() - 1);
                sb.append('[');
                for (int k = 0; k < out.size(); k++) {
                    if (k > 0) sb.append(',');
                    if (out.get(k) == null) sb.append("null"); else sb.append(out.get(k));
                }
                sb.append(']');
            }
        } catch (Exception e) {
            sb.append("null");
        }
    }

    // Java solutions often return List<Integer> or List<List<Integer>> instead of
    // int[] / int[][]; serialise those properly instead of String.valueOf.
    static void writeList(StringBuilder sb, java.util.List<?> items) {
        sb.append('[');
        for (int k = 0; k < items.size(); k++) {
            if (k > 0) sb.append(',');
            writeResult(sb, items.get(k));
        }
        sb.append(']');
    }

    static void writeResult(StringBuilder sb, Object result) {
        if (result == null) { sb.append("null"); return; }
        if (result instanceof int[]) { writeIntArray(sb, (int[]) result); return; }
        if (result instanceof long[]) { writeLongArray(sb, (long[]) result); return; }
        if (result instanceof double[]) { writeDoubleArray(sb, (double[]) result); return; }
        if (result instanceof String[]) { writeStringArray(sb, (String[]) result); return; }
        if (result instanceof int[][]) { writeIntMatrix(sb, (int[][]) result); return; }
        if (result instanceof String) { sb.append('"'); escape(sb, (String) result); sb.append('"'); return; }
        if (result instanceof Boolean) { sb.append(((Boolean) result) ? "true" : "false"); return; }
        if (result instanceof Integer) { sb.append(result); return; }
        if (result instanceof Long) { sb.append(result); return; }
        if (result instanceof Double) { sb.append(result); return; }
        if (result instanceof java.util.List) { writeList(sb, (java.util.List<?>) result); return; }
        String name = result.getClass().getSimpleName();
        if (name.equals("ListNode")) { writeObject(sb, result, true); return; }
        if (name.equals("TreeNode")) { writeObject(sb, result, false); return; }
        sb.append('"');
        escape(sb, String.valueOf(result));
        sb.append('"');
    }

    static Method findMethod(Class<?> cls, String name, int arity) {
        for (Method m : cls.getMethods()) {
            if (m.getName().equals(name) && m.getParameterCount() == arity) return m;
        }
        return null;
    }

    public static void main(String[] argv) {
        try {
            raw = readAll();
        } catch (IOException e) {
            System.err.println("TestCaseError: " + e.getMessage());
            System.exit(4);
            return;
        }
        List<JV> args = new ArrayList<JV>();
        pos = 0;
        skipWs();
        if (pos < raw.length()) {
            JV root = parseValue();
            if (root.t == JV.ARR) args = root.a; else args.add(root);
        }
        Object[] callArgs;
        try {
            callArgs = buildArgs(args);
        } catch (Throwable t) {
            System.err.println("TestCaseError: " + t);
            System.exit(4);
            return;
        }
        Object result;
        try {
            result = invokeSolution(callArgs);
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause() == null ? e : e.getCause();
            System.err.println("RuntimeError: " + cause);
            StackTraceElement[] st = cause.getStackTrace();
            for (int k = 0; k < Math.min(6, st.length); k++) System.err.println("\tat " + st[k]);
            System.exit(1);
            return;
        } catch (Throwable t) {
            System.err.println("RuntimeError: " + t);
            System.exit(1);
            return;
        }
        if (result == null && "__RETURN_SPEC__".equals("ListNode")) {
            // An empty linked list is [] rather than null.
            System.out.print("[]");
            return;
        }
        StringBuilder sb = new StringBuilder();
        writeResult(sb, result);
        System.out.print(sb);
    }

    static String readAll() throws IOException {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[8192];
        int n;
        while ((n = System.in.read(chunk)) > 0) buffer.write(chunk, 0, n);
        return new String(buffer.toByteArray(), "UTF-8");
    }

    static Object invokeSolution(Object[] callArgs) throws Exception {
        int arity = callArgs.length;
        String[] candidates = {FUNCTION_NAME, "Solution", "Main1"};
        Throwable lastError = null;
        for (String className : candidates) {
            Class<?> cls;
            try { cls = Class.forName(className); } catch (Throwable t) { continue; }
            Method m = findMethod(cls, FUNCTION_NAME, arity);
            if (m == null) continue;
            try {
                if (Modifier.isStatic(m.getModifiers())) return m.invoke(null, callArgs);
                Object inst = cls.getDeclaredConstructor().newInstance();
                return m.invoke(inst, callArgs);
            } catch (InvocationTargetException e) {
                throw e;
            } catch (Throwable t) {
                lastError = t;
            }
        }
        if (lastError != null) throw (Exception) lastError;
        System.err.println("RuntimeError: no public method named " + FUNCTION_NAME
                + " taking " + arity + " argument(s) was found. Define "
                + "class Solution { public ... " + FUNCTION_NAME + "(...) { ... } }");
        System.exit(3);
        return null;
    }

    // --- generated argument conversion -------------------------------------
{arg_builders}
}
{node_block}'''

# argument conversion statements, one per parameter
CONVERTERS = {
    "int": "callArgs[{i}] = Integer.valueOf((int) asLong({j}));",
    "long": "callArgs[{i}] = Long.valueOf(asLong({j}));",
    "double": "callArgs[{i}] = Double.valueOf(asDouble({j}));",
    "bool": "callArgs[{i}] = Boolean.valueOf({j}.t == JV.BOOL ? {j}.b : asLong({j}) != 0);",
    "string": "callArgs[{i}] = asString({j});",
    "int[]": "callArgs[{i}] = toIntArray({j});",
    "long[]": "callArgs[{i}] = toLongArray({j});",
    "double[]": "callArgs[{i}] = toDoubleArray({j});",
    "string[]": "callArgs[{i}] = toStringArray({j});",
    "int[][]": "callArgs[{i}] = toIntMatrix({j});",
    "ListNode": "callArgs[{i}] = toList({j});",
    "TreeNode": "callArgs[{i}] = toTree({j});",
}


def public_class_name(source: str) -> str:
    match = re.search(r"\bpublic\s+(?:final\s+|abstract\s+)?class\s+(\w+)", source)
    return match.group(1) if match else "Solution"


def render(source: str, problem) -> dict[str, str]:
    """Return a mapping of filename -> content for the Java compilation unit."""
    from ..typespec import TypeSpec, spec_list, unsupported

    function_name = problem.function_name or "solution"
    params = spec_list(problem.param_spec)
    ret = TypeSpec(problem.return_spec) if problem.return_spec else TypeSpec("void")

    if problem.execution_mode != "function":
        # stdin/stdout program: the user owns the entry point.  Only one file is
        # written (named after their public class) and the runner launches that
        # class, so ``public class Main`` and ``public class Solution`` both work.
        return {f"{public_class_name(source)}.java": source}

    reasons = [u for u in (unsupported(p) for p in params) if u]
    if ret.kind == "unknown":
        reasons.append(unsupported(ret))
    if reasons:
        raise ValueError("; ".join(reasons))

    conversions = []
    for index, spec in enumerate(params):
        converter = CONVERTERS.get(spec.canonical)
        if converter is None:
            raise ValueError(f"Unsupported Java parameter type: {spec.canonical}")
        conversions.append("        " + converter.format(i=index, j=f"arg{index}"))

    body = ["    static Object[] buildArgs(List<JV> args) throws Exception {", "        Object[] callArgs = new Object[%d];" % len(params)]
    for index in range(len(params)):
        body.append("        JV arg%d = %d < args.size() ? args.get(%d) : new JV();" % (index, index, index))
    body.extend(conversions)
    body.append("        return callArgs;")
    body.append("    }")

    node_block = ""
    if nodes.needs_nodes(problem.param_spec, problem.return_spec) and not nodes.user_defines_nodes(source):
        node_block = nodes.JAVA

    main = MAIN.replace("{arg_builders}", "\n".join(body))
    main = main.replace("{node_block}", node_block)
    main = main.replace("FUNCTION_NAME", _java_literal(function_name))
    main = main.replace("__RETURN_SPEC__", ret.canonical)
    return {f"{public_class_name(source)}.java": source, "Main.java": main}


def _java_literal(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
