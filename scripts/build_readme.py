"""Regenerate README.md from README.template.md with the current rule table."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_skills_lint.report import render_rules  # noqa: E402


def main():
    with open(os.path.join(ROOT, "README.template.md")) as fh:
        template = fh.read()
    readme = template.replace("<!-- RULES -->", render_rules("markdown").rstrip("\n"))
    with open(os.path.join(ROOT, "README.md"), "w") as fh:
        fh.write(readme)
    print("README.md written")


if __name__ == "__main__":
    main()
