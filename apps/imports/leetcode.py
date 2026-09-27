"""LeetCode-compatible structured import.

The platform never talks to LeetCode.  Instead you supply a JSON file *you* are
entitled to use -- for example an export produced by a tool you own, or a file
you typed by hand.  Two shapes are understood:

1. **The public GraphQL problem set shape**::

       {
         "data": {
           "problemsetQuestionList": {
             "total": 2,
             "questions": [
               {
                 "questionId": "1",
                 "title": "Two Sum",
                 "titleSlug": "two-sum",
                 "difficulty": "Easy",
                 "topicTags": [{"name": "Array"}, {"name": "Hash Table"}],
                 "content": "<p>Given an array ...</p>",
                 "exampleTestcases": "2\\n[2,7,11,15]\\n9\\n[0,1]",
                 "codeSnippets": [{"lang": "python", "code": "class Solution: ..."}]
               }
             ]
           }
         }
       }

2. **A flat list** of problems using any of the keys the generic importer
   understands (title, description, difficulty, topics, examples, test_cases...).

Test cases are only imported when the file actually contains them.  LeetCode
hides its full test data, and the platform will not invent results: a problem
imported without test cases simply cannot be submitted until you add some in
the admin panel.
"""

from __future__ import annotations

import json
import re

from .base import BaseImporter, ImportValidationError, normalize_problem, strip_html

LANG_MAP = {
    "python": "python",
    "python3": "python",
    "cpp": "cpp",
    "c++": "cpp",
    "cplusplus": "cpp",
    "java": "java",
    "javascript": "javascript",
    "js": "javascript",
    "c": "c",
}

DIFFICULTY_MAP = {
    "EASY": "Easy",
    "MEDIUM": "Medium",
    "HARD": "Hard",
}

EXAMPLE_RE = re.compile(r"^(Example\s*\d*:?)(.*)$", re.IGNORECASE | re.DOTALL)


class LeetCodeImporter(BaseImporter):
    format_name = "leetcode"
    label = "LeetCode JSON"

    def parse(self, raw_text: str) -> dict:
        if not (raw_text or "").strip():
            raise ImportValidationError("The file is empty.")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ImportValidationError(
                f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})."
            )
        if isinstance(data, list):
            return {"name": "LeetCode problems", "problems": data}
        if not isinstance(data, dict):
            raise ImportValidationError("Expected an object or a list at the top level.")

        questions = (
            data.get("data", {}).get("problemsetQuestionList", {}).get("questions")
            or data.get("problems")
            or data.get("questions")
        )
        if questions is None:
            raise ImportValidationError(
                "No problems found. Expected data.problemsetQuestionList.questions, "
                "'problems' or 'questions'."
            )
        if not isinstance(questions, list):
            raise ImportValidationError("'questions' must be a list.")

        problems = [self._convert(question) for question in questions]
        problems = [p for p in problems if p]
        return {
            "name": data.get("name") or "LeetCode problems",
            "description": data.get("description") or "Imported from a user-supplied LeetCode data file.",
            "source": data.get("source") or "LeetCode",
            "problems": problems,
        }

    # -- conversion --------------------------------------------------------
    def _convert(self, question: dict):
        if not isinstance(question, dict):
            return None
        title = (question.get("title") or question.get("name") or "").strip()
        if not title:
            return None

        content = question.get("content") or question.get("description") or ""
        description, examples, constraints = _split_content(content)

        topics = []
        for tag in question.get("topicTags") or question.get("topics") or []:
            if isinstance(tag, dict):
                name = tag.get("name") or tag.get("slug")
            else:
                name = tag
            if name:
                topics.append(str(name).strip())
        domains = _to_domains(topics)

        starter_code = {}
        for snippet in question.get("codeSnippets") or question.get("starter_code") or []:
            if not isinstance(snippet, dict):
                continue
            slug = LANG_MAP.get(str(snippet.get("lang") or snippet.get("language") or "").lower())
            code = snippet.get("code") or snippet.get("starterCode")
            if slug and code:
                starter_code[slug] = code

        payload = {
            "title": title,
            "slug": (question.get("titleSlug") or question.get("slug") or "").strip(),
            "external_id": str(question.get("frontendQuestionId") or question.get("questionId") or question.get("id") or "").strip(),
            "description": description or strip_html(content),
            "difficulty": DIFFICULTY_MAP.get(str(question.get("difficulty") or "").upper(), ""),
            "domains": domains,
            "tags": topics,
            "constraints": constraints or question.get("constraints") or "",
            "examples": question.get("examples") or examples,
            "hints": question.get("hints") or "",
            "source": "LeetCode",
            "source_url": question.get("url")
            or (
                f"https://leetcode.com/problems/{(question.get('titleSlug') or '').strip()}/"
                if question.get("titleSlug")
                else ""
            ),
            "starter_code": starter_code,
        }

        function_name = question.get("function_name")
        if not function_name:
            function_name = _guess_function_name(title, starter_code)
        if function_name:
            payload["function_name"] = function_name
        if question.get("param_spec"):
            payload["param_spec"] = question["param_spec"]
        if question.get("return_spec"):
            payload["return_spec"] = question["return_spec"]
        if question.get("execution_mode"):
            payload["execution_mode"] = question["execution_mode"]

        test_cases = _test_cases_from(question)
        if test_cases:
            payload["test_cases"] = test_cases

        return payload


def _split_content(content: str):
    """Pull the example and constraint blocks out of a rendered description."""
    if not content:
        return "", "", ""
    text = strip_html(content)
    match = EXAMPLE_RE.search(text)
    if not match:
        return text, "", ""
    description = text[: match.start()].strip()
    remainder = text[match.start() :].strip()
    constraint_markers = ("Constraints:", "Constraints：")
    constraints = ""
    for marker in constraint_markers:
        index = remainder.find(marker)
        if index != -1:
            constraints = remainder[index + len(marker) :].strip()
            remainder = remainder[:index].strip()
            break
    return description, remainder, constraints


def _to_domains(topics: list) -> list:
    """Map LeetCode topic tags onto the platform's domain vocabulary."""
    mapping = {
        "array": "Array",
        "hash table": "Hashing",
        "string": "String",
        "linked list": "Linked List",
        "stack": "Stack",
        "queue": "Queue",
        "binary search": "Binary Search",
        "sorting": "Sorting",
        "math": "Math",
        "two pointers": "Two Pointer",
        "matrix": "Matrix",
        "dynamic programming": "Dynamic Programming",
        "greedy": "Greedy",
        "depth-first search": "DFS",
        "breadth-first search": "BFS",
        "tree": "Tree",
        "binary tree": "Binary Tree",
        "binary search tree": "BST",
        "trie": "Trie",
        "heap": "Heap",
        "segment tree": "Segment Tree",
        "bit manipulation": "Bit Manipulation",
        "backtracking": "Backtracking",
        "recursion": "Recursion",
        "sliding window": "Sliding Window",
        "union find": "Union Find",
        "graph": "Graph",
    }
    domains = []
    for topic in topics:
        mapped = mapping.get(topic.lower())
        if mapped and mapped not in domains:
            domains.append(mapped)
    return domains


def _guess_function_name(title: str, starter_code: dict) -> str:
    """Derive a camelCase function name from the title or a starter snippet."""
    match = re.search(r"\b(?:def|function)\s+(\w+)\s*\(", starter_code.get("python", "") + starter_code.get("javascript", ""))
    if match and match.group(1) not in ("__name__",):
        return match.group(1)
    match = re.search(r"public\s+[\w<>\[\]]+\s+(\w+)\s*\(", starter_code.get("java", ""))
    if match:
        return match.group(1)
    words = re.findall(r"[A-Za-z0-9]+", title)
    if not words:
        return "solution"
    name = words[0].lower() + "".join(w.capitalize() for w in words[1:])
    return re.sub(r"[^A-Za-z0-9_]", "", name) or "solution"


def _test_cases_from(question: dict) -> list:
    cases = question.get("test_cases") or question.get("testcases")
    if not cases and question.get("exampleTestcases"):
        cases = _parse_example_testcases(question["exampleTestcases"])
    if not cases:
        return []
    return cases if isinstance(cases, list) else []


def _parse_example_testcases(raw: str) -> list:
    """LeetCode packs examples as lines: count, input, count, output, ..."""
    lines = [line for line in (raw or "").splitlines()]
    cases = []
    index = 0
    while index < len(lines):
        if not lines[index].strip().isdigit():
            index += 1
            continue
        input_count = int(lines[index].strip())
        index += 1
        inputs = []
        for _ in range(input_count):
            if index >= len(lines):
                break
            inputs.append(lines[index].strip())
            index += 1
        if index >= len(lines) or not lines[index].strip().isdigit():
            index += 1
            continue
        output_count = int(lines[index].strip())
        index += 1
        outputs = []
        for _ in range(output_count):
            if index >= len(lines):
                break
            outputs.append(lines[index].strip())
            index += 1
        if not inputs or not outputs:
            continue
        cases.append(
            {
                "input": _as_arg_array(inputs),
                "expected_output": outputs[0] if len(outputs) == 1 else _as_arg_array(outputs),
                "is_sample": True,
            }
        )
    return cases


def _as_arg_array(values: list):
    """Turn raw text lines into the JSON argument array the harness expects."""
    parsed = []
    for value in values:
        parsed.append(_maybe_json(value))
    return json.dumps(parsed)


def _maybe_json(value: str):
    text = value.strip()
    for loader in (json.loads,):
        try:
            return loader(text)
        except (json.JSONDecodeError, ValueError):
            continue
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if text.lstrip("-").isdigit():
        return int(text)
    return text
