import unittest

from agent_skills_lint.frontmatter import FrontmatterError, parse_frontmatter, split_frontmatter

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

SAMPLE = """\
name: pdf-tool
description: >
  Extracts tables from PDFs.
  Use when asked.
license: MIT
metadata:
  author: shri
  version: "1.0"
tags: [a, "b c"]
allowed-tools: "Bash(git:*) Read"
notes: |
  line one
  line two
"""


class SplitTests(unittest.TestCase):
    def test_split_basic(self):
        fm, body, line = split_frontmatter("---\nname: x\n---\n# Body\n")
        self.assertEqual(fm, "name: x")
        self.assertEqual(body, "# Body\n")
        self.assertEqual(line, 4)

    def test_no_frontmatter(self):
        fm, body, line = split_frontmatter("# Just markdown\n")
        self.assertIsNone(fm)
        self.assertEqual(line, 1)

    def test_unclosed(self):
        with self.assertRaises(FrontmatterError):
            split_frontmatter("---\nname: x\n# body\n")

    def test_bom_and_crlf(self):
        fm, body, _ = split_frontmatter("﻿---\r\nname: x\r\n---\r\nbody")
        self.assertEqual(fm, "name: x")


class BuiltinParserTests(unittest.TestCase):
    def parse(self, text):
        return parse_frontmatter(text, use_yaml=False)[0]

    def test_sample(self):
        d = self.parse(SAMPLE)
        self.assertEqual(d["name"], "pdf-tool")
        self.assertEqual(d["description"].strip(), "Extracts tables from PDFs. Use when asked.")
        self.assertEqual(d["metadata"], {"author": "shri", "version": "1.0"})
        self.assertEqual(d["tags"], ["a", "b c"])
        self.assertEqual(d["allowed-tools"], "Bash(git:*) Read")
        self.assertEqual(d["notes"], "line one\nline two\n")

    def test_unquoted_colon_is_error(self):
        with self.assertRaises(FrontmatterError) as cm:
            self.parse("description: Use when: the user asks\n")
        self.assertIn("wrap the value in quotes", str(cm.exception))

    def test_types_match_yaml(self):
        d = self.parse("a: 1.0\nb: true\nc: null\nd: 7\n")
        self.assertEqual(d, {"a": 1.0, "b": True, "c": None, "d": 7})

    def test_duplicate_key(self):
        with self.assertRaises(FrontmatterError):
            self.parse("name: a\nname: b\n")

    def test_nested_metadata_detected(self):
        d = self.parse("metadata:\n  owner:\n    team: x\n")
        self.assertIsInstance(d["metadata"]["owner"], dict)


@unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
class ParserParityTests(unittest.TestCase):
    def test_sample_parity(self):
        a = parse_frontmatter(SAMPLE, use_yaml=False)[0]
        b, which = parse_frontmatter(SAMPLE, use_yaml=True)
        self.assertEqual(which, "pyyaml")
        a["description"] = a["description"].strip()
        b["description"] = b["description"].strip()
        self.assertEqual(a, b)

    def test_both_reject_colon(self):
        for use_yaml in (True, False):
            with self.assertRaises(FrontmatterError):
                parse_frontmatter("description: Use when: asked\n", use_yaml=use_yaml)


if __name__ == "__main__":
    unittest.main()
