"""Semantic checkers for problems whose answer is not unique.

Most problems have one right answer, so plain output comparison is enough.  A few
(backtracking and constructive problems) accept any valid arrangement, and
comparing against a single stored answer would reject correct submissions.  Those
test cases name a checker instead, and the checker validates the actual output
directly.

A checker is a callable ``(actual, args) -> bool``.  ``actual`` is the decoded
JSON value produced by the program (or ``None`` when it is not JSON) and ``args``
is the decoded argument list of the test case being run, so a checker can read
the inputs it needs to validate the answer.
"""

from __future__ import annotations

import json


class CheckerError(ValueError):
    """Raised when a test case names a checker that does not exist."""


def _decode(text):
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _args_of(case_input):
    """Arguments of one test case, as a list of decoded values."""
    value = _decode(case_input)
    if isinstance(value, list):
        return value
    return [value]


def _is_n_queens_board(board, n) -> bool:
    if not isinstance(board, list) or len(board) != n:
        return False
    columns = []
    for row in board:
        if not isinstance(row, str) or len(row) != n:
            return False
        if row.count("Q") != 1:
            return False
        columns.append(row.index("Q"))
    if len(set(columns)) != n:
        return False
    for i, ci in enumerate(columns):
        for j, cj in enumerate(columns):
            if i == j:
                continue
            if abs(i - j) == abs(ci - cj):
                return False
    return True


def n_queens(actual, case_input) -> bool:
    """Accept any set of non-attacking queen placements.

    Finding *every* solution is not a reasonable thing to require, so the
    contract is "at least one valid arrangement": ``actual`` may be a single
    board (the usual LeetCode signature) or a list of distinct boards.  An empty
    list is correct only when the board size has no solution at all.
    """
    args = _args_of(case_input)
    n = args[0] if args and isinstance(args[0], int) and not isinstance(args[0], bool) else None
    if n is None or n < 1:
        return False
    boards = actual
    if boards and isinstance(boards[0], str):
        boards = [boards]
    if not boards:
        return n in (2, 3)
    if not all(_is_n_queens_board(board, n) for board in boards):
        return False
    # Repeating one arrangement says nothing, so require the boards to differ.
    return len({json.dumps(board, sort_keys=True) for board in boards}) == len(boards)


CHECKERS = {
    "n_queens": n_queens,
}


def checker_names() -> list[str]:
    return sorted(CHECKERS)


def outputs_match_checked(actual: str, expected: str, checker: str, case_input="") -> bool:
    """Validate output with a named checker.

    The checker is authoritative: there is no text fallback, otherwise a stored
    answer would silently accept a submission the checker rejected.
    """
    func = CHECKERS.get((checker or "").strip().lower())
    if func is None:
        raise CheckerError(f"Unknown checker: {checker!r}")
    return bool(func(_decode(actual), case_input))
