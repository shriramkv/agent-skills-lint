---
name: agent-skills-lint
description: Lints Agent Skills folders (SKILL.md plus bundled scripts) for spec errors, weak trigger descriptions, broken references and risky code, and grades each skill A to F. Use when the user writes, reviews or installs a skill, or asks whether a skill is safe or well formed.
license: MIT
compatibility: Requires Python 3.9+. No other dependencies.
metadata:
  author: shriramkv
  repository: https://github.com/shriramkv/agent-skills-lint
allowed-tools: "Bash(agent-skills-lint:*) Bash(python3:*) Read"
---

# Lint an Agent Skill

## Steps

1. Find the skill folder. It is the directory that contains `SKILL.md`. A folder of many
   skills can be linted in one go.
2. Run the linter:

   ```bash
   agent-skills-lint check path/to/skills
   ```

   If it is not installed, run `python3 -m agent_skills_lint check path/to/skills` from a
   checkout of the repository.
3. Read the findings from most to least severe. Each one names the rule, the file and line,
   and a fix.
4. For a skill the user plans to install from someone else, treat any **critical** or
   **high** security finding (rules AS2xx) as a reason to stop and show the user the exact
   lines before going further.
5. When fixing the user's own skill, apply the suggested fixes, then run the linter again
   until the grade is A or B.

## Useful options

- `--format markdown` for a report to paste into a pull request.
- `--min-grade B` or `--fail-on high` to make the command exit 1 in CI.
- `--disable AS109` to skip a rule. A single line can be exempted with a trailing comment
  `agent-skills-lint: disable=AS204`.
- `agent-skills-lint rules` lists every rule.

## Edge cases

- A finding in a sample or test file can be intentional. Say so instead of "fixing" it.
- The security rules are pattern based. A clean result lowers risk but is not a full review.
