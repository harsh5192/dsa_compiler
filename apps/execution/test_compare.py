"""Tests for output comparison and the semantic checkers."""

from apps.execution import checkers, compare
from django.test import SimpleTestCase


class CompareTests(SimpleTestCase):
    def test_formatting_does_not_matter(self):
        self.assertTrue(compare.outputs_match("[0, 1]", "[0,1]"))
        self.assertTrue(compare.outputs_match("4", "4.0"))
        self.assertTrue(compare.outputs_match('"abc"', '" abc "'))

    def test_trailing_nulls_are_ignored(self):
        self.assertTrue(compare.outputs_match("[1,2]", "[1,2,null,null]"))
        self.assertTrue(compare.outputs_match("[1,2,null]", "[1,2]"))

    def test_exact_comparison_respects_order(self):
        self.assertFalse(compare.outputs_match("[1,2]", "[2,1]"))

    def test_unordered_comparison_sorts_nested_lists(self):
        self.assertTrue(
            compare.outputs_match('[["b"],["a","c"]]', '[["a","c"],["b"]]', "unordered")
        )

    def test_plain_text_fallback(self):
        self.assertTrue(compare.outputs_match("hello  world", "hello world"))
        self.assertFalse(compare.outputs_match("hello", "world"))

    def test_canonical_handles_mixed_types(self):
        # Sorting must not raise when a list mixes numbers and strings.
        value = compare.canonical([3, "a", None, True], unordered=True)
        self.assertEqual(len(value), 4)


class NQueensCheckerTests(SimpleTestCase):
    def check(self, actual, case_input="[4]"):
        return checkers.outputs_match_checked(actual, "[]", "n_queens", case_input)

    def test_accepts_the_two_solutions_for_four(self):
        self.assertTrue(self.check('[[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]]'))

    def test_accepts_the_solutions_in_any_order(self):
        # Same two solutions, listed the other way round.
        self.assertTrue(self.check('[["..Q.","Q...","...Q",".Q.."],[".Q..","...Q","Q...","..Q."]]'))

    def test_rejects_character_arrays_instead_of_strings(self):
        # Rows must be strings, not lists of single characters.
        self.assertFalse(self.check('[[".","Q",".","."],[".",".",".","Q"],["Q",".",".","."],[".",".","Q","."]]'))

    def test_accepts_a_single_board(self):
        self.assertTrue(self.check('[["Q"]]', "[1]"))

    def test_rejects_attacking_queens(self):
        self.assertFalse(self.check('[["Q.","..Q"],[".Q.","Q.."]]'))
        self.assertFalse(self.check('[["QQ..","....","....","...."]]'))

    def test_rejects_wrong_shape(self):
        self.assertFalse(self.check('[["Q."]]'))
        self.assertFalse(self.check('[["Q"]]', "[4]"))

    def test_empty_answer_only_valid_when_unsolvable(self):
        self.assertTrue(self.check("[]", "[2]"))
        self.assertTrue(self.check("[]", "[3]"))
        self.assertFalse(self.check("[]", "[4]"))

    def test_rejects_repeated_boards(self):
        # The contract asks for distinct arrangements, so a duplicated board adds
        # nothing and is treated as a wrong answer.
        self.assertFalse(
            self.check('[[".Q..","...Q","Q...","..Q."],[".Q..","...Q","Q...","..Q."]]')
        )

    def test_rejects_a_nonsensical_board_size(self):
        self.assertFalse(self.check("[]", "[0]"))
        self.assertFalse(self.check("[]", "[-1]"))
        self.assertFalse(self.check("[]", "[]"))
        self.assertFalse(self.check("[]", '"four"'))

    def test_unknown_checker_raises(self):
        with self.assertRaises(checkers.CheckerError):
            checkers.outputs_match_checked("[]", "[]", "nope", "[4]")
