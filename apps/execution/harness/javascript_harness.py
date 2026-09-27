"""Node.js harness.

``function``-mode problems: stdin carries a JSON array of arguments, stdout
must contain a single JSON value.  ``console.log``/``console.error`` output is
redirected to stderr so it can never corrupt the answer.
"""

from __future__ import annotations

from . import nodes

PREAMBLE = r"""
const __dsaFs = require('fs');

function __dsaReadStdin() {
  try { return __dsaFs.readFileSync(0, 'utf8'); } catch (e) { return ''; }
}

function __dsaBuildList(values) {
  if (!values || values.length === 0) return null;
  const head = new ListNode(0);
  let tail = head;
  for (const v of values) {
    const node = new ListNode(v === null ? 0 : Number(v));
    tail.next = node;
    tail = node;
  }
  return head.next;
}

function __dsaFlatten(node) {
  const out = [];
  let guard = 0;
  while (node && guard < 1e7) { out.push(node.val); node = node.next; guard++; }
  return out;
}

function __dsaBuildTree(values) {
  // Level order, LeetCode style: nulls are placeholders for missing children.
  if (!values || values.length === 0) return null;
  const made = values.map((v) => (v === null ? null : new TreeNode(Number(v))));
  const root = made[0];
  if (root === null) return null;
  let idx = 1;
  const queue = [root];
  while (queue.length) {
    const node = queue.shift();
    if (idx < made.length) node.left = made[idx++];
    if (idx < made.length) node.right = made[idx++];
    if (node.left) queue.push(node.left);
    if (node.right) queue.push(node.right);
  }
  return root;
}

function __dsaTreeValues(node) {
  if (!node) return [];
  const out = [];
  const queue = [node];
  while (queue.length) {
    const cur = queue.shift();
    if (cur === null) { out.push(null); continue; }
    out.push(cur.val);
    queue.push(cur.left);
    queue.push(cur.right);
  }
  while (out.length && out[out.length - 1] === null) out.pop();
  return out;
}

// Keep stray logging out of the answer channel.
const __dsaUserLog = console.log.bind(console);
console.log = (...a) => process.stderr.write(a.map(String).join(' ') + '\n');
console.info = console.log;
console.debug = console.log;
"""

DRIVER_FUNCTION = r'''

// ---------------------------- generated driver ----------------------------
(async () => {
  const __raw = __dsaReadStdin();
  let __args = [];
  if (__raw.trim()) {
    try {
      const __parsed = JSON.parse(__raw);
      __args = Array.isArray(__parsed) ? __parsed : [__parsed];
    } catch (err) {
      process.stderr.write('TestCaseError: could not decode input as JSON: ' + err.message + '\n');
      process.exit(4);
    }
  }

  /*__NODE_ADAPTER__*/

  let __fn = (typeof /*__FUNCTION_NAME__*/ !== 'undefined' && typeof /*__FUNCTION_NAME__*/ === 'function')
    ? /*__FUNCTION_NAME__*/ : null;
  if (!__fn) {
    const __clsRef = typeof Solution !== 'undefined' ? Solution
      : (typeof Main !== 'undefined' ? Main : null);
    if (__clsRef) {
      let __inst = null;
      try { __inst = new __clsRef(); } catch (e) { __inst = null; }
      if (__inst) {
        for (const __m of [/*__FUNCTION_NAME__*/, 'solve', 'run', 'solution']) {
          if (typeof __inst[__m] === 'function') { __fn = __inst[__m].bind(__inst); break; }
        }
      }
    }
  }
  if (!__fn) {
    process.stderr.write('RuntimeError: no callable named ' + /*__FUNCTION_NAME__*/ +
      ' found. Define function ' + /*__FUNCTION_NAME__*/ + '() or class Solution.\n');
    process.exit(3);
  }

  let __result;
  try {
    __result = await __fn(...__args);
  } catch (err) {
    process.stderr.write('RuntimeError: ' + (err && err.stack ? err.stack : String(err)) + '\n');
    process.exit(1);
  }
  if (__result && __result.constructor && __result.constructor.name === 'ListNode') {
    __result = __dsaFlatten(__result);
  } else if (__result && __result.constructor && __result.constructor.name === 'TreeNode') {
    __result = __dsaTreeValues(__result);
  } else if (__result === null && '/*__RETURN__*/' === 'ListNode') {
    __result = [];
  }
  process.stdout.write(JSON.stringify(__result === undefined ? null : __result));
})();
'''

DRIVER_STDIN = r'''

// ---------------------------- generated driver ----------------------------
// stdin/stdout program: nothing extra to wire up.
// --------------------------------------------------------------------------
'''


def render(source: str, problem) -> str:
    from ..typespec import normalize

    function_name = problem.function_name or "solution"
    parts = ["'use strict';"]
    if problem.execution_mode == "function":
        if nodes.needs_nodes(problem.param_spec, problem.return_spec) and not nodes.user_defines_nodes(source):
            parts.append(nodes.JAVASCRIPT)
    parts.append(PREAMBLE)
    parts.append(source)
    if problem.execution_mode == "function":
        lines = []
        for index, spec in enumerate(normalize_list(problem.param_spec)):
            if spec == "ListNode":
                lines.append(f"if (Array.isArray(__args[{index}])) __args[{index}] = __dsaBuildList(__args[{index}]);")
            elif spec == "TreeNode":
                lines.append(f"if (Array.isArray(__args[{index}])) __args[{index}] = __dsaBuildTree(__args[{index}]);")
        adapter = "\n  ".join(lines) if lines else "// no conversions required"
        parts.append(
            DRIVER_FUNCTION.replace("/*__FUNCTION_NAME__*/", function_name)
            .replace("/*__NODE_ADAPTER__*/", adapter)
            .replace("/*__RETURN__*/", problem.return_spec or "")
        )
    else:
        parts.append(DRIVER_STDIN)
    return "\n".join(parts)


def normalize_list(raw):
    """Canonical type names for a param_spec list, whatever shape it arrives in."""
    from ..typespec import spec_list

    if not raw:
        return []
    if all(isinstance(item, str) for item in raw):
        return spec_list([{"name": f"a{i}", "type": item} for i, item in enumerate(raw)]) and [
            s.canonical for s in spec_list([{"name": f"a{i}", "type": item} for i, item in enumerate(raw)])
        ]
    return [spec.canonical for spec in spec_list(raw)]
