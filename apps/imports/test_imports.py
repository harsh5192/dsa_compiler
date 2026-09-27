"""Tests for type normalisation and the import pipeline."""

import json

from django.core.management import call_command
from django.test import TestCase

from apps.execution.typespec import TypeSpec, normalize, spec_list
from apps.imports import base
from apps.problems.models import Problem
from apps.problems.models import TestCase as ProblemTestCase
from apps.sheets.models import Sheet, SheetSection, SheetProblem


class TypeSpecTests(TestCase):
    def test_scalar_aliases(self):
        for text in ("int", "Integer", "int32"):
            self.assertEqual(normalize(text), "int")
        for text in ("long", "int64", "long long"):
            self.assertEqual(normalize(text), "long")
        for text in ("double", "float", "number"):
            self.assertEqual(normalize(text), "double")
        for text in ("bool", "boolean"):
            self.assertEqual(normalize(text), "bool")
        for text in ("str", "String", "char", "text"):
            self.assertEqual(normalize(text), "string")

    def test_array_aliases_and_depth(self):
        for text in ("int[]", "vector<int>", "List<Integer>", "ArrayList<int>"):
            self.assertEqual(normalize(text), "int[]")
        self.assertEqual(normalize("vector<vector<int> >"), "int[][]")
        self.assertEqual(normalize("int[][]"), "int[][]")

    def test_reference_and_const_noise_is_ignored(self):
        self.assertEqual(normalize("const vector<string>&"), "string[]")
        self.assertEqual(normalize("int *"), "int")

    def test_node_types(self):
        self.assertEqual(normalize("ListNode"), "ListNode")
        self.assertEqual(normalize("TreeNode"), "TreeNode")

    def test_unknown_type_is_reported(self):
        spec = TypeSpec("frobnicate")
        self.assertEqual(spec.kind, "unknown")
        warnings = []
        payload = base.normalize_problem(
            {"title": "Mystery", "param_spec": "frobnicate", "return_type": "int"}, warnings
        )
        self.assertTrue(any("frobnicate" in w for w in warnings))
        self.assertTrue(payload["param_spec"])

    def test_spec_list_accepts_dicts_and_strings(self):
        specs = spec_list([{"name": "nums", "type": "int[]"}, "string"])
        self.assertEqual([s.kind for s in specs], ["vector", "scalar"])
        self.assertEqual([s.canonical for s in specs], ["int[]", "string"])

    def test_c_declarations(self):
        self.assertEqual(TypeSpec("int[]").c(), "int*")
        self.assertEqual(TypeSpec("int[][]").c_array_ptr(), "int**")
        self.assertEqual(TypeSpec("string[][]").c_array_ptr(), "char***")
        self.assertEqual(TypeSpec("int[][]").scalar_kind, "int")


class TestCaseSyncTests(TestCase):
    """Re-importing a file must repair, not duplicate, its test cases."""

    def setUp(self):
        call_command("seed_dsa_data", verbosity=0, content_only=True)
        self.problem = Problem.objects.get(slug="two-sum")

    def cases(self):
        return list(self.problem.test_cases.all())

    def test_payload_identity_ignores_formatting(self):
        key_a = base._test_case_key("[[1,2], 3]")
        key_b = base._test_case_key("[[1, 2],3]")
        self.assertEqual(key_a, key_b)

    def test_changing_an_expectation_updates_in_place(self):
        before = self.cases()
        self.assertGreater(len(before), 1)
        target = before[0]
        pk = target.pk
        old_expected = target.expected_output
        incoming = [
            {
                "name": case.name,
                "input_data": case.input_data,
                "expected_output": case.expected_output,
                "explanation": case.explanation,
                "is_sample": case.is_sample,
                "is_hidden": case.is_hidden,
                "order": case.order,
                "comparison": case.comparison,
                "checker": case.checker,
            }
            for case in before
        ]
        incoming[0]["expected_output"] = "[9,9]"
        base.sync_test_cases(self.problem, incoming)
        self.assertNotEqual(old_expected, "[9,9]")
        target.refresh_from_db()
        self.assertEqual(target.pk, pk)
        self.assertEqual(target.expected_output, "[9,9]")
        self.assertEqual(len(self.cases()), len(before))

    def test_removed_cases_are_dropped(self):
        self.assertGreater(len(self.cases()), 1)
        keep = self.cases()[0]
        base.sync_test_cases(
            self.problem,
            [
                {
                    "name": keep.name,
                    "input_data": keep.input_data,
                    "expected_output": keep.expected_output,
                    "explanation": "",
                    "is_sample": True,
                    "is_hidden": False,
                    "order": 0,
                }
            ],
        )
        self.assertEqual(len(self.cases()), 1)

    def test_reformatted_input_does_not_duplicate(self):
        before = self.cases()
        incoming = [
            {
                "name": case.name,
                "input_data": json.dumps(json.loads(case.input_data), indent=2),
                "expected_output": case.expected_output,
                "explanation": case.explanation,
                "is_sample": case.is_sample,
                "is_hidden": case.is_hidden,
                "order": case.order,
                "comparison": case.comparison,
                "checker": case.checker,
            }
            for case in before
        ]
        base.sync_test_cases(self.problem, incoming)
        self.assertEqual(len(self.cases()), len(before))

    def test_cleared_checker_is_not_left_behind(self):
        warnings = []
        payload = base.normalize_problem(
            {
                "title": "Example",
                "checker": "n_queens",
                "param_spec": ["int"],
                "test_cases": [{"input": "[4]", "expected_output": "[]"}],
            },
            warnings,
        )
        self.assertEqual(payload["test_cases"][0]["checker"], "n_queens")
        self.assertEqual(base.sync_test_cases(self.problem, payload["test_cases"]), 1)
        self.assertEqual(self.problem.test_cases.get(input_data="[4]").checker, "n_queens")

        warnings = []
        without = base.normalize_problem(
            {
                "title": "Example",
                "param_spec": ["int"],
                "test_cases": [{"input": "[4]", "expected_output": "[]"}],
            },
            warnings,
        )
        base.sync_test_cases(self.problem, without["test_cases"])
        self.assertEqual(self.problem.test_cases.get(input_data="[4]").checker, "")

    def test_comparison_and_checker_are_persisted(self):
        warnings = []
        cases = base.normalize_test_cases(
            [
                {"input": "[1]", "expected_output": "[1]", "comparison": "unordered"},
                {"input": "[4]", "expected_output": "[]", "checker": "n_queens"},
            ],
            warnings,
            "Example",
        )
        self.assertEqual(cases[0]["comparison"], "unordered")
        self.assertEqual(cases[1]["checker"], "n_queens")
        self.assertEqual(warnings, [])

    def test_unknown_checker_is_reported_and_ignored(self):
        warnings = []
        cases = base.normalize_test_cases(
            [{"input": "[1]", "expected_output": "[1]", "checker": "bogus"}], warnings, "Example"
        )
        self.assertEqual(cases[0]["checker"], "")
        self.assertTrue(any("bogus" in w for w in warnings))

    def test_problem_level_checker_applies_to_every_case(self):
        warnings = []
        cases = base.normalize_test_cases(
            [{"input": "[4]", "expected_output": "[]"}, {"input": "[8]", "expected_output": "[]"}],
            warnings,
            "Example",
            default_checker="n_queens",
        )
        self.assertEqual([c["checker"] for c in cases], ["n_queens", "n_queens"])


class SeedCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_languages", verbosity=0)
        call_command("seed_dsa_data", verbosity=0)

    def test_languages_are_seeded_once(self):
        from apps.execution.models import Language

        self.assertEqual(Language.objects.count(), 5)
        call_command("seed_languages", verbosity=0)
        self.assertEqual(Language.objects.count(), 5)

    def test_sheets_and_problems_exist(self):
        self.assertEqual(Sheet.objects.count(), 4)
        self.assertGreater(Problem.objects.count(), 300)
        self.assertTrue(ProblemTestCase.objects.exists())

    def test_every_test_case_input_is_json(self):
        for case in ProblemTestCase.objects.all():
            with self.subTest(case=case.pk):
                json.loads(case.input_data)

    def test_sheet_entries_have_the_expected_shape(self):
        sheet = Sheet.objects.get(slug="striver-a2z-dsa-sheet")
        self.assertEqual(sheet.sections.count(), 17)
        first = SheetSection.objects.filter(sheet=sheet).order_by("order").first()
        self.assertTrue(first.problems.exists())
        entry = SheetProblem.objects.filter(section=first).first()
        self.assertTrue(entry.problem.title)
        self.assertEqual(entry.section, first)
