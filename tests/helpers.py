import os
import shutil
import tempfile
import textwrap
import unittest

GOOD_FM = """\
name: {name}
description: Converts CSV files into formatted Markdown tables. Use when the user asks to turn a CSV or spreadsheet export into a table for a README or report.
"""

GOOD_BODY = """
# CSV to Markdown

1. Read the CSV.
2. Write the table.
"""


class SkillTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asl-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_skill(self, dir_name="csv-to-markdown", frontmatter=None, body=GOOD_BODY,
                   files=None, raw=None, parent=None):
        root = os.path.join(parent or self.tmp, dir_name)
        os.makedirs(root, exist_ok=True)
        if raw is not None:
            text = raw
        else:
            fm = GOOD_FM.format(name=dir_name) if frontmatter is None else textwrap.dedent(frontmatter)
            text = "---\n" + fm.rstrip("\n") + "\n---\n" + body
        with open(os.path.join(root, "SKILL.md"), "w") as fh:
            fh.write(text)
        for rel, content in (files or {}).items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(content)
        return root

    def rule_ids(self, result):
        return sorted({f.rule_id for f in result.findings})
