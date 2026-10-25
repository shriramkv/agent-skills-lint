# AGENTS.md

Guidance for coding agents working in this repository.

## Project

`agent-skills-lint` is a zero-dependency Python 3.9+ CLI that lints Agent Skills folders.
The package lives in `agent_skills_lint/`:

- `frontmatter.py` parses SKILL.md frontmatter (PyYAML when present, otherwise the built-in subset parser).
- `rules.py` is the single registry of rule ids, severities, summaries and fixes.
- `checks.py` holds the individual spec, quality, security and library checks.
- `engine.py` discovers skills, runs checks, applies suppressions and scores.
- `report.py` and `cli.py` render output and handle gates and exit codes.
- `samples/` holds the bundled good and risky skills used by `demo` and the tests.

## Commands

- Test: `python -m unittest discover -s tests -t .`
- Test the built-in parser path: `AGENT_SKILLS_LINT_NO_YAML=1 python -m unittest discover -s tests -t .`
- Dogfood: `python -m agent_skills_lint check skills --min-grade A`
- Demo: `python -m agent_skills_lint demo`

## Rules for changes

- You must keep the package free of runtime dependencies. PyYAML stays optional.
- You must keep Python 3.9 compatibility: no `match`, no `X | Y` type unions.
- Every new rule must be added to `rules.py`, get at least one positive and one negative test, and appear in the README rule table (regenerate it with `python scripts/build_readme.py`).
- When you fix a false positive, you must add a regression test that pins it.
- You must never make `samples/risky` safe. Its scripts are deliberately unsafe test fixtures and must never be executed.
- Do not print secret values in findings. Report the kind of secret only.
- Do not use em dashes in documentation.
