"""Generate the bundled sheet files from the index and the problem library.

Usage::

    python tools/build_sheet_data.py                # write data/sheets/*.json
    python tools/build_sheet_data.py --stats        # show the match report only
    python tools/build_sheet_data.py --out /tmp/x  # write somewhere else

Every sheet title in ``tools/sheet_index.py`` is looked up in
``tools/problem_library.py``.  Titles that match get the full statement, tags and
test cases; the rest are emitted as title-only entries that you can complete
later from the admin panel or by importing a richer file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

from problem_library import PROBLEMS  # noqa: E402
from sheet_index import SHEETS  # noqa: E402

# Titles whose wording in the popular sheet differs from the library title.
ALIASES = {
    # --- striver a2z -------------------------------------------------------
    "second largest element": "second-largest-element",
    "rotate array": "rotate-array",
    "sort an array of 0s 1s and 2s": "sort-colors",
    "binary search on a sorted array": "binary-search",
    "find a peak element": "find-a-peak-element",
    "kth smallest element": "find-kth-smallest-element",
    "kth smallest largest element in an array": "find-kth-smallest-element",
    "is palindrome": "valid-palindrome",
    "is palindrome efficient": "valid-palindrome",
    "check palindrome": "valid-palindrome",
    "check if a string is a palindrome": "valid-palindrome",
    "valid parenthesis": "valid-parentheses",
    "tries": "implement-trie",
    "string matching": "string-matching",
    "rearrange string": "rearrange-string",
    "traversals": "binary-tree-inorder-traversal",
    "height of a tree": "maximum-depth-of-binary-tree",
    "count nodes in a binary tree": "count-nodes",
    "sum of nodes": "sum-of-nodes",
    "check if a binary tree is identical": "same-tree",
    "identical trees": "same-tree",
    "inorder traversal of a binary tree": "binary-tree-inorder-traversal",
    "preorder traversal": "preorder-traversal",
    "postorder traversal": "postorder-traversal",
    "level order traversal": "binary-tree-level-order-traversal",
    "symmetric tree": "symmetric-tree",
    "diameter of a binary tree": "diameter-of-binary-tree",
    "search a binary tree": "search-in-a-binary-tree",
    "construct a bst from a preorder traversal": "construct-bst-from-preorder",
    "inorder traversal of a bst": "bst-inorder-traversal",
    "insert in a bst": "insert-in-a-bst",
    "delete a node in a bst": "delete-node-in-a-bst",
    "kth largest elements": "kth-largest-elements",
    "n queens": "n-queens",
    "n queens ii": "n-queens",
    "min stack": "min-stack",
    "reverse a linked list": "reverse-linked-list",
    "middle of the linked list": "middle-of-the-linked-list",
    "add two numbers": "add-two-numbers",
    "remove nth node from the end of the linked list": "remove-nth-node-from-end-of-list",
    "maximum sum of two numbers in a linked list": "max-sum-two-linked-list-numbers",
    "merge two sorted linked lists": "merge-two-sorted-linked-lists",
    "check if a binary tree is a bst": "validate-binary-search-tree",
    "validate bst": "validate-binary-search-tree",
    "next greater element": "next-greater-element",
    "next smaller element": "next-greater-element",
    "longest substring with atmost k distinct characters":
        "longest-substring-without-repeating-characters",
    "maximum non repeating characters": "longest-substring-without-repeating-characters",
    "longest substring without repeating characters":
        "longest-substring-without-repeating-characters",
    # --- striver old -------------------------------------------------------
    "second largest": "second-largest-element",
    "missing number in an array": "missing-number",
    "array maximum equal": "array-maximum-equal",
    "kadanes algorithm": "kadanes-algorithm-max-subarray-sum",
    "kadanes algorithm max subarray sum": "kadanes-algorithm-max-subarray-sum",
    "maximum subarray": "maximum-subarray",
    "rotate array": "rotate-array",
    "remove duplicates": "remove-duplicates-from-sorted-array",
    "sort the colors": "sort-colors",
    "sort colors": "sort-colors",
    "sort the array": "sort-an-array",
    "sort an array": "sort-an-array",
    "binary search": "binary-search",
    "count occurrences": "first-and-last-position-of-target",
    "single element in a sorted array": "single-element-sorted-array",
    "detect cycle in a linked list": "linked-list-cycle",
    "delete nth node from the end of linked list": "remove-nth-node-from-end-of-list",
    "add two numbers represented as a linked list": "add-two-numbers",
    "maximum sum of two numbers in a linked list": "max-sum-two-linked-list-numbers",
    "traversal": "binary-tree-inorder-traversal",
    "height of tree": "maximum-depth-of-binary-tree",
    "longest increasing subsequence": "longest-increasing-subsequence",
    "ways to climb stairs": "climbing-stairs",
    "maximum sum non adjacent elements": "house-rober",
    "number of islands": "number-of-islands",
    "two pointer technique": "rotate-array",
    "merge two sorted arrays": "merge-two-sorted-arrays",
    # --- love babbar -------------------------------------------------------
    "validate parentheses": "valid-parentheses",
    "move all zeroes to the end": "move-zeroes",
    "max sum without adjacents 2": "house-rober",
    "climbing stairs": "climbing-stairs",
    "coin change": "coin-change",
    "longest increasing subsequence": "longest-increasing-subsequence",
    "longest common subsequence": "longest-common-subsequence",
    "partition equal subset sum": "partition-equal-subset-sum",
    "next greater element": "next-greater-element",
    "check if a string is a palindrome": "valid-palindrome",
    "reverse a string": "reverse-string",
    "longest substring without repeating characters":
        "longest-substring-without-repeating-characters",
    "k largest elements": "kth-largest-elements",
    "container with most water": "container-with-most-water",
    "bfs": "bfs-traversal",
    "bfs traversal": "bfs-traversal",
    "dfs": "dfs-traversal",
    "dfs traversal": "dfs-traversal",
    "number of islands": "number-of-islands",
    "maximum depth of a binary tree": "maximum-depth-of-binary-tree",
    "identical trees": "same-tree",
    "minimum jumps to reach the end of an array": "min-jumps",
    "smallest number of jumps": "min-jumps",
    "group anagrams": "group-anagrams",
    "valid anagram": "valid-anagram",
    "two sum": "two-sum",
    "3 sum": "3sum",
    "kadanes algorithm": "kadanes-algorithm-max-subarray-sum",
    "reverse an array": "reverse-an-array",
    "rotate array by k": "rotate-array",
    "bubble sort": "bubble-sort",
    "merge sort": "merge-sort",
    "second largest": "second-largest-element",
    "missing number": "missing-number",
    "fibonacci number": "fibonacci-number",
    "count set bits": "count-set-bits",
    "matrix spiral traversal": "matrix-spiral-traversal",
    "spiral matrix": "matrix-spiral-traversal",
    "set matrix zeroes": "set-matrix-zeroes",
    "search in 2d matrix": "search-a-2d-matrix",
    "search in a rotated sorted array": "search-in-rotated-sorted-array",
    "permutations": "permutations",
    "construct a trie from words": "implement-trie",
    "trie": "implement-trie",
    "binary tree inorder traversal": "binary-tree-inorder-traversal",
    "reverse a linked list": "reverse-linked-list",
    "add two numbers represented as linked lists": "add-two-numbers",
    "level order traversal": "binary-tree-level-order-traversal",
}

# Titles that are intentionally left as placeholders: the problem requires a
# representation the JSON test format cannot express.
SKIP_SLUGS = set()


def norm(text: str) -> str:
    text = re.sub(r"^\s*[\d.]+\s*-?\s*", "", str(text or ""))  # "3.1 - "
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class Matcher:
    def __init__(self, problems: list):
        self.by_norm = {}
        self.by_slug = {}
        for problem in problems:
            self.by_slug[problem["slug"]] = problem
            self.by_norm.setdefault(norm(problem["title"]), problem)
        self.unmatched = []

    def match(self, title: str):
        key = norm(title)
        if key in self.by_norm:
            return self.by_norm[key], "exact"
        alias = ALIASES.get(key)
        if alias and alias in self.by_slug:
            return self.by_slug[alias], "alias"
        # Drop a leading/trailing qualifier such as "(Approach 2)".
        simple = re.sub(r"\s*\(approach \d+\)$", "", key).strip()
        if simple in self.by_norm:
            return self.by_norm[simple], "loose"
        return None, ""


def build_sheet(slug: str, meta: dict, steps: list, matcher: Matcher) -> dict:
    sections = []
    for index, (step_name, items) in enumerate(steps):
        problems = []
        for title, difficulty, domains in items:
            problem, how = matcher.match(title)
            if problem and problem["slug"] not in SKIP_SLUGS:
                payload = dict(problem)
                # The sheet's own classification is authoritative for the index.
                payload["difficulty"] = difficulty
                payload["domains"] = list(domains)
                payload.pop("match", None)
                problems.append(payload)
            else:
                matcher.unmatched.append((slug, step_name, title))
                problems.append(
                    {
                        "title": title,
                        "difficulty": difficulty,
                        "domains": list(domains),
                        "tags": list(domains),
                        "description": "",
                        "notes": "Title only: import a richer file to add the statement and tests.",
                    }
                )
        sections.append({"name": step_name, "order": index, "problems": problems})
    return {
        "name": meta["name"],
        "description": meta["description"],
        "source": meta["source"],
        "version": meta["version"],
        "sections": sections,
    }


SAMPLE_META = {
    "name": "Starter Problems (full content)",
    "description": (
        "Every problem that ships with a written statement and test cases, "
        "grouped by domain. This is the sheet to import when you want content "
        "rather than an index."
    ),
    "source": "Bundled with this project",
    "version": "1.0",
}

# Display order for the domain sections of the starter sheet.
DOMAIN_ORDER = [
    "Array",
    "String",
    "Sorting",
    "Binary Search",
    "Hashing",
    "Two Pointer",
    "Sliding Window",
    "Linked List",
    "Stack",
    "Queue",
    "Heap",
    "Tree",
    "BST",
    "Trie",
    "Graph",
    "Dynamic Programming",
    "Backtracking",
    "Greedy",
    "Bit Manipulation",
    "Math",
    "Design",
    "Matrix",
    "Recursion",
    "Union Find",
    "Segment Tree",
    "Fenwick Tree",
    "Basics",
]


def build_sample_sheet() -> dict:
    """Group the whole library by its first domain, so nothing is orphaned."""
    buckets: dict = {}
    for problem in PROBLEMS:
        domain = (problem.get("domains") or ["Other"])[0]
        buckets.setdefault(domain, []).append(dict(problem))

    def rank(domain: str) -> int:
        return DOMAIN_ORDER.index(domain) if domain in DOMAIN_ORDER else len(DOMAIN_ORDER)

    sections = []
    for index, domain in enumerate(sorted(buckets, key=lambda d: (rank(d), d))):
        sections.append(
            {
                "name": domain,
                "order": index,
                "description": f"{len(buckets[domain])} problems about {domain.lower()}.",
                "problems": sorted(buckets[domain], key=lambda p: p["title"]),
            }
        )
    return {**SAMPLE_META, "sections": sections}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "data" / "sheets"))
    parser.add_argument(
        "--sample-out", default=str(ROOT / "data" / "samples" / "sample_problems.json")
    )
    parser.add_argument("--stats", action="store_true", help="only print the report")
    parser.add_argument("--quiet", action="store_true", help="hide the placeholder list")
    args = parser.parse_args(argv)

    matcher = Matcher(PROBLEMS)
    out_dir = Path(args.out)
    if not args.stats:
        out_dir.mkdir(parents=True, exist_ok=True)

    total_entries = 0
    filled_entries = 0
    for slug, meta in SHEETS.items():
        sheet = build_sheet(slug, meta, meta["steps"], matcher)
        entries = sum(len(section["problems"]) for section in sheet["sections"])
        filled = sum(
            1
            for section in sheet["sections"]
            for problem in section["problems"]
            if problem.get("test_cases")
        )
        total_entries += entries
        filled_entries += filled
        if not args.stats:
            path = out_dir / f"{slug}.json"
            path.write_text(json.dumps(sheet, indent=2, ensure_ascii=False) + "\n")
        print(f"{slug:14s} {len(sheet['sections']):3d} sections  {entries:4d} entries  {filled:3d} with tests")

    used = {p["slug"] for p in PROBLEMS}
    referenced = set()
    for slug, meta in SHEETS.items():
        for _step_name, items in meta["steps"]:
            for title, _difficulty, _domains in items:
                problem, _how = matcher.match(title)
                if problem:
                    referenced.add(problem["slug"])

    print()
    print(f"library problems      : {len(PROBLEMS)}")
    print(f"referenced by sheets  : {len(referenced)}")
    print(f"only in starter sheet : {len(used - referenced)}")
    for slug in sorted(used - referenced):
        print(f"  - {slug}")
    print()
    print(f"sheet entries         : {total_entries}")
    print(f"entries with tests    : {filled_entries} ({100.0 * filled_entries // max(total_entries, 1)}%)")
    print(f"title-only placeholders: {len(matcher.unmatched)}")
    if matcher.unmatched and "--quiet" not in sys.argv:
        for sheet_slug, step_name, title in matcher.unmatched:
            print(f"  - {sheet_slug} / {step_name}: {title}")

    if not args.stats:
        sample_path = Path(args.sample_out)
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        sample = build_sample_sheet()
        sample_path.write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n")
        cases = sum(len(p.get("test_cases", [])) for p in PROBLEMS)
        print()
        print(
            f"wrote starter sheet: {sample_path.name} "
            f"({len(sample['sections'])} sections, {len(PROBLEMS)} problems, {cases} test cases)"
        )
        print(f"wrote {len(SHEETS)} files to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
