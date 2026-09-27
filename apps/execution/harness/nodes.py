"""Structures for the built-in ``ListNode`` / ``TreeNode`` helper types.

A problem only needs these when its parameter or return spec mentions them.
The generators below emit the definitions *only* when the user's own source
does not already define them, so both styles work:

* LeetCode style -- the user pastes the node classes in their solution.
* Minimal style  -- the user writes ``def solution(head)`` and the platform
  supplies the nodes.

``test_case.input_data`` for these problems is a plain JSON array, e.g.::

    [[1, 2, 3, 4, 5]]        # head
    [1, 2, 3, null, 5]       # tree in level order
"""

from __future__ import annotations


def needs_nodes(param_spec, return_spec) -> bool:
    specs = [str(s) for s in (param_spec or [])] + [str(return_spec or "")]
    return any("ListNode" in s or "TreeNode" in s for s in specs)


def user_defines_nodes(source: str) -> bool:
    """Heuristic: did the user paste their own node classes?"""
    src = source or ""
    return (
        "class ListNode" in src
        or "class TreeNode" in src
        or "struct ListNode" in src
        or "struct TreeNode" in src
    )


PYTHON = '''

# --- provided by the platform (ListNode / TreeNode helper types) ---
class ListNode:
    __slots__ = ("val", "next")

    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    __slots__ = ("val", "left", "right")

    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
# --- end platform helpers ---
'''


JAVASCRIPT = """

// --- provided by the platform (ListNode / TreeNode helper types) ---
class ListNode {
  constructor(val = 0, next = null) { this.val = val; this.next = next; }
}
class TreeNode {
  constructor(val = 0, left = null, right = null) {
    this.val = val; this.left = left; this.right = right;
  }
}
// --- end platform helpers ---
"""


CPP = """
// --- provided by the platform (ListNode / TreeNode helper types) ---
struct ListNode {
    int val;
    ListNode* next;
    ListNode(int v = 0) : val(v), next(nullptr) {}
};

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int v = 0) : val(v), left(nullptr), right(nullptr) {}
};
// --- end platform helpers ---
"""


JAVA = """
// --- provided by the platform (ListNode / TreeNode helper types) ---
// Package-private top level classes so Solution.java can use them too.
class ListNode {
    int val;
    ListNode next;
    ListNode() {}
    ListNode(int v) { val = v; }
}

class TreeNode {
    int val;
    TreeNode left, right;
    TreeNode() {}
    TreeNode(int v) { val = v; }
}
// --- end platform helpers ---
"""


C = """
/* --- provided by the platform (ListNode / TreeNode helper types) --- */
typedef struct ListNode {
    int val;
    struct ListNode *next;
} ListNode;

typedef struct TreeNode {
    int val;
    struct TreeNode *left;
    struct TreeNode *right;
} TreeNode;
/* --- end platform helpers --- */
"""
