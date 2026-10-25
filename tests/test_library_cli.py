import contextlib
import io
import json
import os
import unittest

from agent_skills_lint.cli import SAMPLES_DIR, main
from agent_skills_lint.engine import discover, lint_paths
from tests.helpers import SkillTestCase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class LibraryTests(SkillTestCase):
    def test_discovery_and_nesting(self):
        lib = os.path.join(self.tmp, "lib")
        self.make_skill("one", parent=lib)
        self.make_skill("two", parent=os.path.join(lib, "group"))
        os.makedirs(os.path.join(lib, "node_modules", "pkg"))
        with open(os.path.join(lib, "node_modules", "pkg", "SKILL.md"), "w") as fh:
            fh.write("---\nname: pkg\n---\n")
        names = [os.path.basename(d) for d in discover(lib)]
        self.assertEqual(names, ["two", "one"] if names[0] == "two" else ["one", "two"])
        self.assertEqual(len(names), 2)

    def test_duplicate_names(self):
        lib = os.path.join(self.tmp, "lib")
        self.make_skill("alpha", parent=lib)
        self.make_skill("alpha", parent=os.path.join(lib, "copy"))
        report = lint_paths([lib], overlap=0)
        self.assertTrue(all("AS301" in self.rule_ids(s) for s in report.skills))

    def test_description_overlap(self):
        lib = os.path.join(self.tmp, "lib")
        fm = ("name: {n}\ndescription: Converts CSV files into formatted Markdown tables. Use when the "
              "user asks to turn CSV exports into tables{x}.\n")
        self.make_skill("csv-a", parent=lib, frontmatter=fm.format(n="csv-a", x=""))
        self.make_skill("csv-b", parent=lib, frontmatter=fm.format(n="csv-b", x=" for reports"))
        report = lint_paths([lib])
        self.assertIn("AS302", self.rule_ids(report.skills[1]))
        self.assertNotIn("AS302", self.rule_ids(lint_paths([lib], overlap=0).skills[1]))

    def test_overall_is_worst_of(self):
        lib = os.path.join(self.tmp, "lib")
        self.make_skill("good-one", parent=lib)
        self.make_skill("bad-one", parent=lib, body="\n")
        report = lint_paths([lib])
        self.assertEqual(report.score, min(s.score for s in report.skills))
        self.assertLess(report.score, 100)

    def test_no_skills_found(self):
        report = lint_paths([self.tmp])
        self.assertEqual(self.rule_ids(report.skills[0]), ["AS001"])


class CliTests(SkillTestCase):
    def test_demo_runs(self):
        code, out, _ = run_cli("demo")
        self.assertEqual(code, 0)
        self.assertIn("pdf-table-extractor", out)
        self.assertIn("A (100)", out)
        self.assertIn("Overall: F", out)

    def test_samples_good_is_clean_and_risky_hits_every_category(self):
        report = lint_paths([SAMPLES_DIR])
        good, risky = sorted(report.skills, key=lambda s: s.score, reverse=True)
        self.assertEqual(good.findings, [])
        cats = {f.rule.category for f in risky.findings}
        self.assertEqual(cats, {"spec", "quality", "security"})
        self.assertEqual(risky.grade, "F")

    def test_shorthand_and_json(self):
        code, out, _ = run_cli(self.make_skill(), "--format", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["overall"]["grade"], "A")
        self.assertEqual(data["skills"][0]["name"], "csv-to-markdown")

    def test_gates(self):
        root = self.make_skill(files={"scripts/x.sh": "sudo rm -rf /\n"})
        self.assertEqual(run_cli("check", root)[0], 0)
        self.assertEqual(run_cli("check", root, "--min-grade", "B")[0], 1)
        self.assertEqual(run_cli("check", root, "--fail-on", "critical")[0], 1)
        clean = self.make_skill("clean-one", frontmatter="name: clean-one\ndescription: Formats CSV "
                                "files as Markdown tables. Use when asked to tabulate CSV data.\n")
        self.assertEqual(run_cli("check", clean, "--min-grade", "A", "--fail-on", "low")[0], 0)

    def test_markdown_and_badge(self):
        root = self.make_skill()
        code, out, _ = run_cli("check", root, "--format", "markdown")
        self.assertIn("| Skill | Path | Grade |", out)
        self.assertIn("img.shields.io", out)
        code, out, _ = run_cli("check", root, "--format", "badge")
        self.assertEqual(json.loads(out)["message"], "A (100)")

    def test_output_file(self):
        target = os.path.join(self.tmp, "report.json")
        run_cli("check", self.make_skill(), "--format", "json", "-o", target)
        with open(target) as fh:
            self.assertEqual(json.load(fh)["tool"], "agent-skills-lint")

    def test_usage_errors(self):
        self.assertEqual(run_cli("check", os.path.join(self.tmp, "nope"))[0], 2)
        self.assertEqual(run_cli("check", self.make_skill(), "--disable", "AS999")[0], 2)
        self.assertEqual(run_cli("check", self.make_skill(), "--disable", "orphan-file")[0], 0)

    def test_rules_listing(self):
        code, out, _ = run_cli("rules", "--format", "json")
        ids = [r["id"] for r in json.loads(out)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("AS201", ids)

    def test_repo_dogfood_skill_is_grade_a(self):
        report = lint_paths([os.path.join(ROOT, "skills")])
        self.assertEqual(report.grade, "A", [f for _, f in report.findings()])


if __name__ == "__main__":
    unittest.main()
