# Changelog

## 0.1.0 (2026-10-25)

First release.

- 36 rules across four layers: spec (AS0xx), quality (AS1xx), security (AS2xx) and library (AS3xx).
- A to F grading per skill, worst-of overall grade, critical findings cap a skill at D.
- `check`, `rules`, `demo` and `version` commands; console, JSON, Markdown and shields.io badge output.
- `--min-grade` and `--fail-on` CI gates, `--disable` and inline `agent-skills-lint: disable=` suppressions.
- Zero runtime dependencies; optional PyYAML with a tested built-in parser fallback.
- Bundled good and risky sample skills, and the repo's own skill linted at grade A in CI.
- Calibrated against 42 production skills with regression tests for every false positive found.
