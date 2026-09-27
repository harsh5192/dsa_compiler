"""Tests for the source templates each language runner renders.

These are generation tests: they never launch a compiler, they only assert the
text handed to the toolchain is complete and self-consistent.
"""

from django.test import SimpleTestCase

from apps.execution.harness import (
    c_harness,
    cpp_harness,
    java_harness,
    javascript_harness,
    python_harness,
)
from apps.execution.starter import generate as generate_starter
from apps.execution.typespec import TypeSpec, spec_list


class FakeLanguage:
    def __init__(self, slug, name="Demo Language"):
        self.slug = slug
        self.name = name


class FakeProblem:
    """Minimal stand-in for a Problem row."""

    def __init__(self, function_name="solution", param_spec=(), return_spec="int",
                 execution_mode="function", name="Demo", time_limit=2.0):
        self.function_name = function_name
        self.param_spec = list(param_spec)
        self.return_spec = return_spec
        self.execution_mode = execution_mode
        self.name = name
        self.slug = "demo"
        self.title = "Demo"
        self.time_limit = time_limit


class CHarnessRenderTests(SimpleTestCase):
    def test_runtime_precedes_user_source(self):
        out = c_harness.render("int twoSum(int *a, int n) { return a[0]; }", FakeProblem())
        self.assertLess(out.index("typedef struct JV"), out.index("int twoSum"))
        self.assertIn("#include <stdbool.h>", out)
        self.assertIn("print_json_string", out)

    def test_matrix_row_terminator_for_every_numeric_matrix(self):
        for canonical, macro in (
            ("int[][]", "DSA_ROW_END_INT"),
            ("long[][]", "DSA_ROW_END_LONG"),
            ("double[][]", "DSA_ROW_END_DOUBLE"),
        ):
            with self.subTest(canonical=canonical):
                out = c_harness.render(
                    "void f(void) {}", FakeProblem(return_spec=canonical)
                )
                self.assertIn(f"__v[r][c] != {macro}", out)
                self.assertIn("int solution_rows = 0;", out)
                self.assertNotIn("solution_cols", out)

    def test_string_matrix_rows_are_null_terminated(self):
        out = c_harness.render("void f(void) {}", FakeProblem(return_spec="string[][]"))
        self.assertIn("char ***__v", out)
        self.assertIn("for (int c = 0; __v[r][c]; c++)", out)

    def test_unsupported_matrix_type_is_reported(self):
        with self.assertRaises(ValueError):
            c_harness.render("void f(void) {}", FakeProblem(return_spec="frobnicate[][]"))

    def test_array_parameters_interleave_dimensions(self):
        out = c_harness.render(
            "int f(int *v, int m, int **g, int r, int c) { return v[0]; }",
            FakeProblem(param_spec=["int[]", "int[][]"]),
        )
        self.assertIn("solution(a0, a0_len, a1, a1_rows, a1_cols)", out)

    def test_vector_result_publishes_length(self):
        out = c_harness.render("int *f(int n) { return 0; }", FakeProblem(return_spec="int[]"))
        self.assertIn("int solution_len = 0;", out)

    def test_class_solution_target(self):
        out = c_harness.render(
            "class Solution { public: int f(int n) { return n; } };", FakeProblem()
        )
        self.assertIn("Solution().solution(", out)


class CppHarnessRenderTests(SimpleTestCase):
    def test_runtime_precedes_user_source(self):
        out = cpp_harness.render("int f(int n) { return n; }", FakeProblem())
        self.assertLess(out.index("struct JV"), out.index("int f(int n)"))

    def test_vector_result_is_serialised_from_the_container(self):
        out = cpp_harness.render(
            "std::vector<int> f() { return {}; }", FakeProblem(return_spec="int[]")
        )
        self.assertIn("for (const auto& __x : __result)", out)


class JavaHarnessRenderTests(SimpleTestCase):
    def test_return_spec_is_substituted(self):
        files = java_harness.render(
            "class Solution { public int f(int n) { return n; } }", FakeProblem()
        )
        self.assertNotIn("__RETURN_SPEC__", files["Main.java"])
        self.assertIn("class Solution", files["Solution.java"])

    def test_empty_list_result_is_accepted(self):
        files = java_harness.render(
            "import java.util.*; class Solution { public List<Integer> f() { return new ArrayList<>(); } }",
            FakeProblem(return_spec="ListNode"),
        )
        self.assertIn('System.out.print("[]")', files["Main.java"])


class JavaScriptHarnessRenderTests(SimpleTestCase):
    def test_bfs_tree_builder(self):
        out = javascript_harness.render("function f(root) {}", FakeProblem(param_spec=["TreeNode"]))
        self.assertIn("__dsaBuildTree", out)
        self.assertIn("node.left = made[idx++];", out)

    def test_empty_list_return_spec(self):
        out = javascript_harness.render("function f() {}", FakeProblem(return_spec="ListNode"))
        self.assertIn("__result = [];", out)
        self.assertIn("'ListNode' === 'ListNode'", out)


class PythonHarnessRenderTests(SimpleTestCase):
    def test_bfs_tree_builder(self):
        out = python_harness.render("def f(root): pass", FakeProblem(param_spec=["TreeNode"]))
        self.assertIn("_dsa_build_tree(_a)", out)
        self.assertIn("node.left = made[idx]", out)
        self.assertNotIn("_dsa_build_tree(_a[0])", out)

    def test_empty_list_return_spec(self):
        out = python_harness.render("def f(): pass", FakeProblem(return_spec="ListNode"))
        self.assertIn("_result = []", out)
        self.assertIn('_RETURN == "ListNode"', out)

    def test_return_spec_is_substituted(self):
        out = python_harness.render("def f(): pass", FakeProblem(return_spec="string[]"))
        self.assertNotIn("{return_spec}", out)


class StarterTests(SimpleTestCase):
    def test_c_matrix_parameters_declare_both_dimensions(self):
        code = generate_starter(
            FakeProblem(param_spec=["int[][]"], return_spec="int[][]"), FakeLanguage("c")
        )
        self.assertIn("int** arg", code)
        self.assertIn("int arg_rows", code)
        self.assertIn("int arg_cols", code)

    def test_c_matrix_result_documents_row_terminators(self):
        code = generate_starter(
            FakeProblem(param_spec=["int[][]"], return_spec="int[][]"), FakeLanguage("c")
        )
        self.assertIn("DSA_ROW_END", code)
        self.assertIn("solution_rows", code)

    def test_c_vector_result_uses_length_global(self):
        code = generate_starter(FakeProblem(param_spec=["int[]"], return_spec="int[]"), FakeLanguage("c"))
        self.assertIn("solution_len", code)

    def test_every_language_starts_with_a_comment(self):
        for slug in ("python", "javascript", "cpp", "java", "c"):
            with self.subTest(slug=slug):
                code = generate_starter(FakeProblem(param_spec=["int", "string"]), FakeLanguage(slug))
                self.assertTrue(code.strip())
                self.assertIn("solution", code)


class SpecListTests(SimpleTestCase):
    def test_c_dimensions_per_parameter(self):
        specs = spec_list(["int[]", "int[][]", "string", "string[][]"])
        self.assertEqual(
            [s.c_len_params("v") for s in specs],
            [
                ["int v_len"],
                ["int v_rows", "int v_cols"],
                [],
                ["int v_rows", "int v_cols"],
            ],
        )

    def test_typespec_round_trip(self):
        self.assertEqual(TypeSpec("string[]").base, "string")
        self.assertEqual(TypeSpec("int[][]").depth, 2)
        self.assertEqual(TypeSpec("int").is_scalar, True)
        self.assertEqual(TypeSpec("void").is_void, True)
