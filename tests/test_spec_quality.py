import os
import unittest

from agent_skills_lint.engine import lint_skill
from tests.helpers import GOOD_BODY, SkillTestCase


class SpecTests(SkillTestCase):
    def lint(self, root):
        return lint_skill(root, use_yaml=False)

    def test_clean_skill_scores_100(self):
        r = self.lint(self.make_skill())
        self.assertEqual(r.findings, [])
        self.assertEqual((r.score, r.grade), (100, "A"))

    def test_missing_skill_md(self):
        root = os.path.join(self.tmp, "empty-skill")
        os.makedirs(root)
        r = self.lint(root)
        self.assertEqual(self.rule_ids(r), ["AS001"])
        self.assertLessEqual(r.score, 69)

    def test_lowercase_filename(self):
        root = self.make_skill()
        os.rename(os.path.join(root, "SKILL.md"), os.path.join(root, "skill.md"))
        self.assertIn("AS001", self.rule_ids(self.lint(root)))

    def test_no_frontmatter(self):
        r = self.lint(self.make_skill(raw="# Title\n\nSome text\n"))
        self.assertIn("AS002", self.rule_ids(r))

    def test_unparseable_frontmatter(self):
        r = self.lint(self.make_skill(frontmatter="name: csv-to-markdown\ndescription: Use when: x\n"))
        self.assertIn("AS002", self.rule_ids(r))

    def test_name_rules(self):
        cases = {
            "Bad_Name": ["AS004", "AS005"],
            "-lead": ["AS004", "AS005"],
            "two--hyphens": ["AS004", "AS005"],
            "x" * 65: ["AS004", "AS005"],
        }
        for name, expected in cases.items():
            fm = "name: %s\ndescription: Formats CSV files as Markdown tables. Use when asked to tabulate CSV data.\n" % name
            r = self.lint(self.make_skill(dir_name="csv-to-markdown", frontmatter=fm))
            for rule in expected:
                self.assertIn(rule, self.rule_ids(r), name)

    def test_name_dir_mismatch_only(self):
        fm = "name: other-name\ndescription: Formats CSV files as Markdown tables. Use when asked to tabulate CSV data.\n"
        self.assertEqual(self.rule_ids(self.lint(self.make_skill(frontmatter=fm))), ["AS005"])

    def test_missing_name_and_description(self):
        r = self.lint(self.make_skill(frontmatter="license: MIT\n"))
        self.assertIn("AS003", self.rule_ids(r))
        self.assertIn("AS006", self.rule_ids(r))

    def test_description_too_long(self):
        fm = "name: csv-to-markdown\ndescription: Use when converting CSV. %s\n" % ("word " * 250)
        self.assertIn("AS007", self.rule_ids(self.lint(self.make_skill(frontmatter=fm))))

    def test_compatibility_too_long(self):
        fm = ("name: csv-to-markdown\ndescription: Formats CSV files as Markdown tables. Use when asked to "
              "tabulate CSV data.\ncompatibility: %s\n" % ("x" * 501))
        self.assertIn("AS008", self.rule_ids(self.lint(self.make_skill(frontmatter=fm))))

    def test_metadata_non_string(self):
        fm = ("name: csv-to-markdown\ndescription: Formats CSV files as Markdown tables. Use when asked to "
              "tabulate CSV data.\nmetadata:\n  version: 1.0\n")
        self.assertIn("AS009", self.rule_ids(self.lint(self.make_skill(frontmatter=fm))))

    def test_allowed_tools_list_and_broad(self):
        fm = ("name: csv-to-markdown\ndescription: Formats CSV files as Markdown tables. Use when asked to "
              "tabulate CSV data.\nallowed-tools: [Bash, Read]\n")
        ids = self.rule_ids(self.lint(self.make_skill(frontmatter=fm)))
        self.assertIn("AS010", ids)
        self.assertIn("AS212", ids)

    def test_scoped_tools_ok(self):
        fm = ("name: csv-to-markdown\ndescription: Formats CSV files as Markdown tables. Use when asked to "
              "tabulate CSV data.\nallowed-tools: \"Bash(git:*) Bash(npm run:*) Read\"\n")
        self.assertEqual(self.rule_ids(self.lint(self.make_skill(frontmatter=fm))), [])

    def test_unknown_field_and_reserved(self):
        fm = ("name: claude-helper\ndescription: Formats CSV files as Markdown tables. Use when asked to "
              "tabulate CSV data.\ntriggers: csv\n")
        ids = self.rule_ids(self.lint(self.make_skill(dir_name="claude-helper", frontmatter=fm)))
        self.assertEqual(ids, ["AS011", "AS012"])


class QualityTests(SkillTestCase):
    def lint(self, root):
        return lint_skill(root, use_yaml=False)

    def test_short_vague_description(self):
        fm = "name: csv-to-markdown\ndescription: Helps with stuff.\n"
        ids = self.rule_ids(self.lint(self.make_skill(frontmatter=fm)))
        self.assertIn("AS101", ids)
        self.assertIn("AS102", ids)

    def test_trigger_phrases_accepted(self):
        for d in ("Formats CSV files as tables. Use this skill whenever a CSV must become Markdown.",
                  "Formats CSV files as tables for READMEs, invoked when the user pastes CSV data.",
                  "Formats CSV files as Markdown tables when the user wants a readable table."):
            fm = "name: csv-to-markdown\ndescription: %s\n" % d
            self.assertNotIn("AS102", self.rule_ids(self.lint(self.make_skill(frontmatter=fm))), d)

    def test_more_trigger_phrasings(self):
        for d in ("Guidance for distinctive visual design when building new UI or reshaping an existing one.",
                  "Read this skill before the first step that uses the built-in browser pane.",
                  "Formats CSV data as Markdown tables if the user pastes a CSV export."):
            fm = "name: csv-to-markdown\ndescription: %s\n" % d
            self.assertNotIn("AS102", self.rule_ids(self.lint(self.make_skill(frontmatter=fm))), d)

    def test_links_in_code_are_sample_text(self):
        body = GOOD_BODY + "\nWrite the line `- [Voice](voice.md) read this first` to the index.\n"
        self.assertNotIn("AS106", self.rule_ids(self.lint(self.make_skill(body=body))))
        body = GOOD_BODY + "\n```markdown\nSee [notes](notes.md)\n```\n"
        self.assertNotIn("AS106", self.rule_ids(self.lint(self.make_skill(body=body))))

    def test_orphans_aggregate_and_package_coverage(self):
        files = {"scripts/office/soffice.py": "x\n", "scripts/office/pack.py": "x\n",
                 "scripts/office/schemas/a.xsd": "x\n", "scripts/other/a.py": "x\n",
                 "scripts/other/b.py": "x\n"}
        body = GOOD_BODY + "\nRun `python scripts/office/soffice.py`.\n"
        r = self.lint(self.make_skill(body=body, files=files))
        orphans = [f for f in r.findings if f.rule_id == "AS109"]
        self.assertEqual(len(orphans), 1)
        self.assertIn("2 bundled files", orphans[0].message)

    def test_first_person(self):
        fm = ("name: csv-to-markdown\ndescription: I can format CSV files as Markdown tables. "
              "Use when asked to tabulate CSV data.\n")
        self.assertIn("AS103", self.rule_ids(self.lint(self.make_skill(frontmatter=fm))))

    def test_empty_body(self):
        self.assertIn("AS104", self.rule_ids(self.lint(self.make_skill(body="\n\n"))))

    def test_long_body(self):
        body = "\n".join("Line %d of instructions." % i for i in range(520))
        self.assertIn("AS105", self.rule_ids(self.lint(self.make_skill(body=body))))

    def test_references(self):
        body = GOOD_BODY + (
            "\nRun `scripts/run.py`, see [guide](references/guide.md), "
            "[missing](references/nope.md), `scripts/gone.sh`, "
            "[abs](/etc/hosts), [up](../other/SKILL.md) and [web](https://example.org/x).\n")
        r = self.lint(self.make_skill(body=body, files={
            "scripts/run.py": "print('hi')\n",
            "references/guide.md": "# Guide\n",
        }))
        msgs = [(f.rule_id, f.message) for f in r.findings]
        broken = sorted(m for rid, m in msgs if rid == "AS106")
        self.assertEqual(broken, ["'references/nope.md' does not exist", "'scripts/gone.sh' does not exist"])
        self.assertEqual(len([1 for rid, _ in msgs if rid == "AS107"]), 2)

    def test_reference_line_numbers(self):
        body = "\n# T\n\nSee [g](references/missing.md).\n"
        r = self.lint(self.make_skill(body=body))
        f = [f for f in r.findings if f.rule_id == "AS106"][0]
        with open(os.path.join(r.path, "SKILL.md")) as fh:
            self.assertIn("references/missing.md", fh.read().split("\n")[f.line - 1])

    def test_nested_reference(self):
        body = GOOD_BODY + "\nSee [a](references/a.md).\n"
        r = self.lint(self.make_skill(body=body, files={
            "references/a.md": "Also read [b](references/b.md)\n",
            "references/b.md": "deep\n",
        }))
        ids = self.rule_ids(r)
        self.assertIn("AS108", ids)
        self.assertNotIn("AS109", ids)  # b.md is reachable, just one level too deep

    def test_orphans_and_dir_mentions(self):
        r = self.lint(self.make_skill(files={"scripts/lonely.py": "print(1)\n"}))
        self.assertIn("AS109", self.rule_ids(r))
        body = GOOD_BODY + "\nHelpers live in scripts/ if you need them.\n"
        r = self.lint(self.make_skill(dir_name="csv-to-markdown2", body=body,
                                      frontmatter="name: csv-to-markdown2\ndescription: Formats CSV files "
                                      "as Markdown tables. Use when asked to tabulate CSV data.\n",
                                      files={"scripts/lonely.py": "print(1)\n"}))
        self.assertNotIn("AS109", self.rule_ids(r))

    def test_oversized_reference(self):
        body = GOOD_BODY + "\nSee references/big.md.\n"
        r = self.lint(self.make_skill(body=body, files={"references/big.md": "x" * 70000}))
        self.assertIn("AS110", self.rule_ids(r))


if __name__ == "__main__":
    unittest.main()
