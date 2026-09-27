"""Web layer tests: pages render, routes resolve, the JSON API behaves.

These deliberately use the real templates and the real service for one cheap
function-mode problem, because the interesting failures (a template typo, a
custom case that silently loses its input) only show up end to end.
"""

import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from apps.execution import service
from apps.execution.models import Language
from apps.execution.views import _parse_custom_cases
from apps.problems.models import (
    Difficulty,
    Domain,
    ExecutionMode,
    Problem,
    UserPreference,
)
from apps.problems.models import TestCase as ProblemTestCase
from apps.progress.models import ProblemProgress, ProgressStatus  # noqa: F401
from apps.sheets.models import Sheet, SheetProblem, SheetSection
from apps.submissions.models import Submission, Verdict

TWO_SUM = (
    "def twoSum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [seen[target - n], i]\n"
    "        seen[n] = i\n"
    "    return []\n"
)

WRONG_TWO_SUM = "def twoSum(nums, target):\n    return [0, 0]\n"


class WebTestCase(TestCase):
    """Shared fixture: one user with a password, and one small problem."""

    @classmethod
    def setUpTestData(cls):
        """A self-contained fixture: the real language rows, one small problem.

        The web tests must pass on a freshly created test database, so nothing
        here depends on ``seed_dsa_data`` having been run first.
        """
        call_command("seed_languages", verbosity=0)
        cls.user = get_user_model().objects.create_user(
            username="solver", password="correct-horse-battery"
        )
        domain, _ = Domain.objects.get_or_create(
            name="Arrays", slug="arrays"
        )
        cls.problem = Problem.objects.create(
            title="Two Sum",
            slug="two-sum",
            primary_domain=domain,
            description="Given an array of integers and a target, return the indices.",
            difficulty=Difficulty.EASY,
            execution_mode=ExecutionMode.FUNCTION,
            function_name="twoSum",
            param_spec=[{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}],
            return_spec="int[]",
            input_format="nums: int[]\ntarget: int",
            output_format="int[]",
            examples="Input: [[2,7,11,15], 9]\nOutput: [0,1]",
            constraints="1 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9",
            hints="One hash map is enough.\nStore the value you have already seen.",
            expected_time_complexity="O(n)",
            expected_space_complexity="O(n)",
            time_limit=5.0,
            memory_limit_mb=256,
        )
        for order, (data, expected) in enumerate(
            [
                ("[[2,7,11,15], 9]", "[0,1]"),
                ("[[3,2,4], 6]", "[1,2]"),
                ("[[3,3], 6]", "[0,1]"),
            ],
            start=1,
        ):
            ProblemTestCase.objects.create(
                problem=cls.problem,
                name=f"Sample {order}",
                input_data=data,
                expected_output=expected,
                is_sample=True,
                order=order,
            )
        ProblemTestCase.objects.create(
            problem=cls.problem,
            name="Hidden case",
            input_data="[[1,2,3,9], 11]",
            expected_output="[1,3]",
            is_hidden=True,
            order=4,
        )
        cls.sheet = Sheet.objects.create(name="Smoke Sheet", slug="smoke-sheet")
        section = SheetSection.objects.create(sheet=cls.sheet, name="Basics", order=1)
        SheetProblem.objects.create(section=section, problem=cls.problem, order=1)
        cls.python = Language.objects.get(slug="python")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        self.csrf = self.get_csrf()

    def get_csrf(self) -> str:
        self.client.get(self.problem.get_absolute_url())
        return self.client.cookies["csrftoken"].value

    def post_json(self, url, payload, *, csrf=True):
        headers = {"x-csrftoken": self.csrf} if csrf else {}
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            headers=headers,
        )


class PageTests(WebTestCase):
    def test_every_page_renders(self):
        routes = [
            reverse("dashboard:index"),
            reverse("problems:list"),
            reverse("sheets:list"),
            reverse("progress:index"),
            reverse("submissions:list"),
            reverse("accounts:settings"),
            reverse("accounts:login"),
            reverse("manifest"),
            reverse("offline"),
            reverse("service-worker"),
        ]
        for url in routes:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_register_page_is_reachable_when_signed_out(self):
        response = Client().get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Create an account", response.content.decode())

    def test_register_redirects_a_signed_in_user_home(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_problem_page_shows_statement_editor_and_api_urls(self):
        response = self.client.get(self.problem.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("function", body.lower())  # function-mode signature block
        self.assertIn(reverse("execution:run"), body)
        self.assertIn(reverse("execution:submit"), body)
        self.assertIn("code-input", body)

    def test_problem_list_filters(self):
        base = reverse("problems:list")
        for query in ["?difficulty=Easy", "?sort=difficulty", "?q=two", "?nonsense=1"]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(base + query).status_code, 200)
        empty = self.client.get(base + "?q=zzz-no-such-problem").content.decode()
        self.assertIn("No problem matches", empty)

    def test_sheet_list_shows_every_sheet_with_progress(self):
        response = self.client.get(reverse("sheets:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["sheet_cards"]), 1)
        card = response.context["sheet_cards"][0]
        self.assertEqual(card["problems"], 1)
        self.assertEqual(card["solved"], 0)
        self.assertIn(self.sheet.name, response.content.decode())

    def test_sheet_detail_marks_solved_problems(self):
        ProblemProgress.objects.create(
            user=self.user, problem=self.problem, status=ProgressStatus.SOLVED
        )
        body = self.client.get(self.sheet.get_absolute_url()).content.decode()
        self.assertIn("1 / 1 solved", body)
        self.assertIn("status-solved", body)

    def test_dashboard_sheet_cards_carry_progress(self):
        body = self.client.get(reverse("dashboard:index")).content.decode()
        self.assertIn(self.sheet.name, body)
        card = self.client.get(reverse("dashboard:index")).context["sheet_cards"][0]
        self.assertEqual(card["percent"], 0.0)

    def test_sheet_detail_renders(self):
        sheet = self.sheet
        response = self.client.get(sheet.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(sheet.name, response.content.decode())

    def test_sheet_counts_ignore_removed_slots(self):
        sheet = Sheet.objects.filter(slug="smoke-sheet").with_sections().first()
        self.assertEqual(sheet.problem_count, 1)
        self.assertEqual(sheet.section_count, 1)
        self.assertEqual(sheet.problem_ids, {self.problem.pk})

        entry = SheetProblem.objects.get(section__sheet=sheet)
        entry.is_removed = True
        entry.save(update_fields=["is_removed"])

        hidden = Sheet.objects.filter(slug="smoke-sheet").with_sections().first()
        self.assertEqual(hidden.problem_count, 0)
        self.assertEqual(hidden.problem_ids, set())

    def test_submission_detail_renders(self):
        problem = self.problem
        Submission.objects.create(
            user=self.user,
            problem=problem,
            language=self.python,
            source_code=TWO_SUM,
            verdict=Verdict.ACCEPTED,
            test_cases_passed=3,
            total_test_cases=3,
        )
        url = reverse("submissions:detail", args=[Submission.objects.latest("id").pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_pages_require_a_signed_in_user(self):
        anonymous = Client()
        for url in [
            reverse("dashboard:index"),
            reverse("problems:list"),
            reverse("sheets:list"),
            reverse("progress:index"),
            reverse("submissions:list"),
            reverse("accounts:settings"),
        ]:
            with self.subTest(url=url):
                response = anonymous.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response.headers["Location"])


class PreferenceTests(WebTestCase):
    def test_context_processor_exposes_preferences(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertIn("preference", response.context)
        self.assertEqual(response.context["preference"].user, self.user)

    def test_settings_form_saves_theme_and_default_language(self):
        cpp = Language.objects.get(slug="cpp")
        response = self.client.post(
            reverse("accounts:settings"),
            {
                "theme": "dark",
                "editor": "plain",
                "editor_theme": "vs",
                "editor_font_size": "18",
                "autosave_delay_ms": "2000",
                "execution_timeout": "3",
                "autosave": "on",
                "default_language": cpp.slug,
            },
        )
        self.assertEqual(response.status_code, 302)
        preference = UserPreference.for_user(self.user)
        self.assertEqual(preference.theme, "dark")
        self.assertEqual(preference.editor, "plain")
        self.assertEqual(preference.editor_font_size, 18)
        self.assertEqual(preference.default_language_id, cpp.pk)
        self.assertTrue(preference.autosave)

    def test_settings_form_rejects_unknown_values(self):
        self.client.post(
            reverse("accounts:settings"),
            {"theme": "neon", "editor": "vim", "editor_font_size": "999",
             "autosave_delay_ms": "5", "execution_timeout": "abc", "default_language": "klingon"},
        )
        preference = UserPreference.for_user(self.user)
        self.assertIn(preference.theme, dict(UserPreference.THEME_CHOICES))
        self.assertIn(preference.editor, ("monaco", "plain"))
        self.assertLessEqual(preference.editor_font_size, 28)
        self.assertGreaterEqual(preference.autosave_delay_ms, 300)
        self.assertIsNone(preference.default_language_id)


class CustomCaseParsingTests(TestCase):
    """The custom input box is user typed; these are the shapes it accepts."""

    def test_single_argument_list_is_one_case(self):
        cases = _parse_custom_cases("[[2, 7, 11, 15], 9]")
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["input_data"], "[[2, 7, 11, 15], 9]")
        self.assertEqual(cases[0]["expected_output"], "")

    def test_list_of_argument_lists_is_several_cases(self):
        cases = _parse_custom_cases("[[[2, 7], 9], [[3, 3], 6]]")
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]["label"], "Custom case 1")
        self.assertEqual(cases[1]["label"], "Custom case 2")

    def test_dict_case_keeps_its_expected_output(self):
        cases = _parse_custom_cases('{"input": "[[2,7], 9", "expected_output": "[0,1]"}')
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["expected_output"], "[0,1]")

    def test_non_json_text_is_a_raw_stdin_case(self):
        cases = _parse_custom_cases("hello world")
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["input_data"], "hello world")

    def test_empty_and_bogus_input_yield_nothing(self):
        for raw in ["", "   ", None, 12, True]:
            with self.subTest(raw=raw):
                self.assertEqual(_parse_custom_cases(raw), [])


class ServiceFieldAccessTests(WebTestCase):
    """Custom cases reach the judge as dicts, stored ones as model rows."""

    def test_case_field_reads_dicts_and_models(self):
        case = self.problem.sample_test_cases[0]
        self.assertEqual(service.case_field(case, "input_data"), case.input_data)
        self.assertEqual(
            service.case_field({"input_data": "x"}, "input_data"), "x"
        )
        self.assertEqual(service.case_field({"input_data": None}, "input_data", ""), "")
        self.assertEqual(service.case_field(object(), "input_data", "fallback"), "fallback")

    def test_custom_case_receives_its_input(self):
        report = service.execute(
            problem=self.problem,
            language=Language.objects.get(slug="python"),
            source_code=TWO_SUM,
            mode="run",
            custom_cases=_parse_custom_cases("[[2,7,11,15], 9]"),
        )
        result = report.cases[0]
        self.assertEqual(result.input_data, "[[2, 7, 11, 15], 9]")
        self.assertEqual(result.actual_output, "[0, 1]")


class ApiTests(WebTestCase):
    def test_run_accepts_correct_code(self):
        response = self.post_json(
            reverse("execution:run"),
            {"problem": self.problem.slug, "language": "python", "code": TWO_SUM},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["report"]["verdict"], "accepted")
        self.assertEqual(data["report"]["test_cases_passed"], data["report"]["total_test_cases"])
        self.assertEqual(data["complexity"]["time"], "O(n)")

    def test_run_reports_wrong_answer(self):
        response = self.post_json(
            reverse("execution:run"),
            {"problem": self.problem.slug, "language": "python", "code": WRONG_TWO_SUM},
        )
        self.assertEqual(response.json()["report"]["verdict"], "wrong_answer")

    def test_run_rejects_unknown_problem_and_language(self):
        for payload in [
            {"problem": "nope", "language": "python", "code": TWO_SUM},
            {"problem": self.problem.slug, "language": "cobol", "code": TWO_SUM},
        ]:
            with self.subTest(payload=payload):
                response = self.post_json(reverse("execution:run"), payload)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])

    def test_run_requires_code(self):
        response = self.post_json(
            reverse("execution:run"),
            {"problem": self.problem.slug, "language": "python", "code": "   "},
        )
        self.assertEqual(response.json()["report"]["verdict"], "empty_submission")

    def test_custom_case_without_expected_output_is_informational(self):
        response = self.post_json(
            reverse("execution:run"),
            {
                "problem": self.problem.slug,
                "language": "python",
                "code": TWO_SUM,
                "custom_cases": "[[2,7,11,15], 9]",
            },
        )
        case = response.json()["report"]["cases"][0]
        self.assertEqual(case["verdict"], "custom")
        self.assertEqual(case["actual_output"], "[0, 1]")

    def test_custom_case_with_expected_output_is_judged(self):
        response = self.post_json(
            reverse("execution:run"),
            {
                "problem": self.problem.slug,
                "language": "python",
                "code": TWO_SUM,
                "custom_cases": '{"input": "[[2,7,11,15], 9]", "expected_output": "[0,1]"}',
            },
        )
        self.assertEqual(response.json()["report"]["cases"][0]["verdict"], "accepted")

    def test_submit_records_a_submission_and_progress(self):
        response = self.post_json(
            reverse("execution:submit"),
            {"problem": self.problem.slug, "language": "python", "code": TWO_SUM},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["report"]["verdict"], "accepted")
        self.assertTrue(data["progress"]["solved"])

        submission = Submission.objects.get(pk=data["submission_id"])
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.verdict, Verdict.ACCEPTED)
        self.assertEqual(submission.test_results.count(), submission.total_test_cases)

        progress = ProblemProgress.objects.get(
            user=self.user, problem=self.problem
        )
        self.assertEqual(progress.status, ProgressStatus.SOLVED)
        self.assertTrue(progress.is_solved)
        self.assertEqual(progress.last_language_id, self.python.pk)
        self.assertEqual(
            self.client.get(data["submission_url"]).status_code, 200
        )

    def test_submit_failure_leaves_progress_unsolved(self):
        response = self.post_json(
            reverse("execution:submit"),
            {"problem": self.problem.slug, "language": "python", "code": WRONG_TWO_SUM},
        )
        data = response.json()
        self.assertEqual(data["report"]["verdict"], "wrong_answer")
        self.assertFalse(data["progress"]["solved"])
        progress = ProblemProgress.objects.get(user=self.user, problem=self.problem)
        self.assertEqual(progress.status, ProgressStatus.ATTEMPTED)

    def test_run_saves_code_and_starter_endpoint_returns_one(self):
        self.post_json(
            reverse("execution:run"),
            {"problem": self.problem.slug, "language": "python", "code": TWO_SUM},
        )
        saved = self.problem.saved_codes.get(user=self.user, language=self.python)
        self.assertEqual(saved.code, TWO_SUM)

        response = self.client.get(
            reverse("execution:starter", args=[self.problem.slug]),
            {"language": "cpp"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("cpp", body["monaco_language"])
        self.assertIn("twoSum", body["code"])

    def test_save_endpoint_and_oversized_code(self):
        response = self.post_json(
            reverse("execution:save-code"),
            {"problem": self.problem.slug, "language": "python", "code": "x = 1"},
        )
        self.assertEqual(response.json()["saved"], 5)

        response = self.post_json(
            reverse("execution:save-code"),
            {
                "problem": self.problem.slug,
                "language": "python",
                "code": "#" * (256 * 1024 + 1),
            },
        )
        self.assertEqual(response.status_code, 413)

    def test_endpoints_require_post(self):
        for name in ["execution:run", "execution:submit", "execution:save-code"]:
            with self.subTest(endpoint=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 405)

    def test_endpoints_enforce_csrf(self):
        # The default test client skips CSRF, so build a strict one.
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        for name in ["execution:run", "execution:submit", "execution:save-code"]:
            with self.subTest(endpoint=name):
                response = strict.post(
                    reverse(name),
                    data=json.dumps(
                        {
                            "problem": self.problem.slug,
                            "language": "python",
                            "code": TWO_SUM,
                        }
                    ),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 403)

    def test_starter_endpoint_rejects_unknown_language(self):
        response = self.client.get(
            reverse("execution:starter", args=[self.problem.slug]),
            {"language": "cobol"},
        )
        self.assertEqual(response.status_code, 404)
