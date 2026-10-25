# agent-skills-lint

Lint, grade and security-check [Agent Skills](https://agentskills.io/specification) folders before
you ship or install them.

[![CI](https://github.com/shriramkv/agent-skills-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/shriramkv/agent-skills-lint/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

Agent Skills is the open format for packaging reusable agent expertise as a folder: a `SKILL.md`
with `name` and `description` frontmatter, plus optional `scripts/`, `references/` and
`assets/`. It is one of the projects of the [Agentic AI Foundation (AAIF)](https://aaif.io/projects).

A skill is code and instructions that an agent loads into its context and may execute. That makes
two questions matter before anyone uses it:

1. **Will the agent find and use it well?** Is the description clear about *when* to trigger, are
   the referenced files really there, is the body small enough to load?
2. **Is it safe to install?** Do the bundled scripts pipe downloads into a shell, read
   `~/.aws/credentials` or hardcode a token? Does the instruction text tell the agent to hide
   things from the user?

`agent-skills-lint` answers both in one command, grades every skill A to F, and gates CI.

```text
$ agent-skills-lint demo -q
agent-skills-lint 0.1.0 | 2 skills scanned

ok   pdf-table-extractor  A (100)  good/pdf-table-extractor
FAIL Risky_Helper         F (  0)  risky/risky-helper

Findings: 3 critical, 8 high, 7 medium, 2 low
Overall: F (0) worst-of across skills; mean score 50.0
```

## How it relates to `skills-ref`

The reference library's `skills-ref validate` checks that frontmatter is valid and names follow
the convention. `agent-skills-lint` covers the same spec rules and adds three more layers on top:

| Layer | What it checks | `skills-ref` | `agent-skills-lint` |
|---|---|---|---|
| Spec | frontmatter, name format, name matches directory, field limits | yes | yes |
| Quality | trigger wording, body size, broken or absolute references, reference chains, orphan files | | yes |
| Security | curl-pipe-shell, destructive deletes, encoded exec, eval, sudo, secrets, credential stores, prompt injection, hidden text, broad `allowed-tools` | | yes |
| Library | duplicate names and overlapping descriptions across a folder of skills | | yes |

Use both if you like. They do not conflict.

## Install

```bash
pip install git+https://github.com/shriramkv/agent-skills-lint
```

No runtime dependencies. If PyYAML is installed it is used to parse frontmatter; otherwise a
built-in parser handles the YAML subset that skills use. Both paths are tested in CI.

## Usage

```bash
# one skill, a SKILL.md path, or a whole folder of skills
agent-skills-lint check path/to/skills
agent-skills-lint path/to/skills            # "check" is the default

# reports
agent-skills-lint check skills --format markdown -o report.md
agent-skills-lint check skills --format json
agent-skills-lint check skills --format badge   # shields.io endpoint JSON

# CI gates (exit 1 when they fail)
agent-skills-lint check skills --min-grade B
agent-skills-lint check skills --fail-on high

# tuning
agent-skills-lint check skills --disable AS109,description-first-person
agent-skills-lint check skills --overlap 0.7     # AS302 threshold, 0 turns it off

agent-skills-lint rules                          # list every rule
agent-skills-lint demo                           # run on the bundled good and risky samples
```

Exempt a single line with a trailing comment:

```python
value = eval(expr)  # agent-skills-lint: disable=AS204
```

Exit codes: `0` passed, `1` a gate failed, `2` usage error.

## Grading

Each skill starts at 100 and loses points per finding: critical 40, high 20, medium 8, low 3.
Any critical finding caps the skill at 69 (grade D), so a dangerous script can never hide behind
otherwise good documentation. Grades: A 90+, B 80+, C 70+, D 60+, F below 60.

When you lint a folder, the overall grade is the **worst** skill's grade (the report also shows
the mean), because one unsafe skill in a library is enough to cause harm.

## Rules

| Rule | Slug | Severity | Category | Checks | Fix |
|---|---|---|---|---|---|
| AS001 | `missing-skill-md` | critical | spec | Skill directory has no SKILL.md | Add a SKILL.md with name and description frontmatter at the skill root |
| AS002 | `invalid-frontmatter` | critical | spec | SKILL.md frontmatter is missing or cannot be parsed | Open SKILL.md with a '---' YAML block holding name and description; quote values containing ': ' |
| AS003 | `name-missing` | high | spec | Frontmatter has no name | Add name: <lowercase-hyphenated-id> matching the directory name |
| AS004 | `name-invalid` | high | spec | name breaks the spec format (1-64 chars of a-z, 0-9 and single hyphens) | Use lowercase letters, digits and single hyphens, with no leading or trailing hyphen |
| AS005 | `name-dir-mismatch` | high | spec | name does not match the parent directory name | Rename the directory or the name so they are identical |
| AS006 | `description-missing` | high | spec | Frontmatter has no description | Add a description saying what the skill does and when to use it |
| AS007 | `description-too-long` | high | spec | description exceeds 1024 characters | Trim the description to the essentials and move detail into the body |
| AS008 | `compatibility-invalid` | medium | spec | compatibility must be a 1-500 character string | State only the product, packages or network access the skill needs |
| AS009 | `metadata-invalid` | medium | spec | metadata must map string keys to string values | Quote numeric or boolean values and avoid nested structures |
| AS010 | `allowed-tools-invalid` | medium | spec | allowed-tools must be one space-separated string | Write it as allowed-tools: "Bash(git:*) Read" |
| AS011 | `unknown-field` | low | spec | Frontmatter field is not defined by the spec | Move custom keys under metadata |
| AS012 | `name-reserved-word` | low | spec | name contains a word some platforms reserve (anthropic, claude) | Pick a vendor-neutral name |
| AS101 | `description-too-short` | medium | quality | description is too short for an agent to match tasks against | Say what it does, what inputs it handles and when to use it, in 1-3 sentences |
| AS102 | `description-no-trigger` | medium | quality | description says what the skill does but not when to use it | Add a 'Use when ...' clause naming the tasks and keywords that should trigger it |
| AS103 | `description-first-person` | low | quality | description is written in first person | Write in third person, for example 'Extracts tables from PDFs ...' |
| AS104 | `body-empty` | high | quality | SKILL.md has no instructions after the frontmatter | Add step-by-step instructions, examples and edge cases |
| AS105 | `body-too-long` | medium | quality | SKILL.md body is over the recommended 500 lines or about 5000 tokens | Move detail into references/ and link it from SKILL.md |
| AS106 | `broken-reference` | high | quality | SKILL.md references a file that does not exist | Fix the path or add the missing file |
| AS107 | `non-portable-reference` | medium | quality | Reference uses an absolute path or points outside the skill | Use a path relative to the skill root, such as scripts/run.py |
| AS108 | `nested-reference` | low | quality | A referenced file points on to further files (reference chain) | Link every file directly from SKILL.md, one level deep |
| AS109 | `orphan-file` | low | quality | Bundled file is never mentioned in SKILL.md | Reference it from SKILL.md so the agent knows it exists, or remove it |
| AS110 | `oversized-reference` | low | quality | Reference file is large and expensive to load into context | Split it into smaller, focused files |
| AS201 | `curl-pipe-shell` | critical | security | Downloads remote code and pipes it straight into an interpreter | Pin a version, download to a file, verify a checksum, then run it |
| AS202 | `destructive-delete` | critical | security | Recursive delete of /, ~ or $HOME | Delete only paths inside a temp or project directory |
| AS203 | `encoded-exec` | critical | security | Decodes and executes an encoded payload | Ship readable source instead of encoded code |
| AS204 | `dynamic-eval` | high | security | Evaluates dynamically built code (eval, exec, new Function) | Parse the data explicitly instead of evaluating it |
| AS205 | `shell-injection-risk` | medium | security | Runs commands through a shell (shell=True, os.system, exec) | Pass an argument list to subprocess.run without shell=True |
| AS206 | `privilege-escalation` | high | security | Uses sudo or makes files world-writable | Run without elevated privileges and use narrow file permissions |
| AS207 | `hardcoded-secret` | high | security | Looks like a hardcoded credential | Read secrets from environment variables or a secret manager |
| AS208 | `plaintext-http` | medium | security | Contacts a remote host over plain http:// | Use https:// |
| AS209 | `credential-access` | high | security | Reads a local credential store (~/.ssh, ~/.aws/credentials, .netrc ...) | Ask the user for the specific credential instead of reading the store |
| AS210 | `prompt-injection` | high | security | Instruction text tries to override the agent's rules or hide actions from the user | Remove the override wording; a skill should never ask the agent to deceive or bypass safeguards |
| AS211 | `hidden-content` | medium | security | Markdown contains invisible characters or HTML comments the user will not see rendered | Remove zero-width characters and move comment text into visible prose |
| AS212 | `broad-allowed-tools` | medium | security | allowed-tools pre-approves unrestricted shell access | Scope it, for example Bash(git:*) instead of Bash |
| AS301 | `duplicate-name` | high | library | Two skills share the same name | Give every skill a unique name |
| AS302 | `description-overlap` | medium | library | Two skills have near-identical descriptions, so agents may pick the wrong one | Make each description name its distinct inputs and trigger |

Security rules are pattern based. They skip commented-out lines, scan fenced code blocks in
Markdown (agents copy and run those), ignore XML namespace URIs, and treat quoted phrases such as
`"ignore previous instructions"` as examples rather than instructions. A clean result lowers risk;
it is not a substitute for reading a skill you do not trust.

### Calibrated on real skills

Before release the linter was run against 42 production skills (document, spreadsheet, slide,
browser, research and workflow skills). All of them graded A or B, with no security false
positives. Each false positive found along the way is pinned by a regression test.

## Use it in CI

```yaml
# .github/workflows/skills.yml
name: Lint skills
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install git+https://github.com/shriramkv/agent-skills-lint
      - run: agent-skills-lint check skills --min-grade B --fail-on high --format markdown -o lint.md
      - if: always()
        run: cat lint.md >> "$GITHUB_STEP_SUMMARY"
```

## Use it from an agent

This repository ships its own skill at [`skills/agent-skills-lint`](skills/agent-skills-lint/SKILL.md).
Install it next to your other skills and an agent can lint a skill before installing or
publishing it. CI lints that skill with this tool and requires grade A.

## Part of an AAIF toolchain

`agent-skills-lint` sits alongside the author's other open source checkers for AAIF projects,
including [`agentsmd-lint`](https://github.com/shriramkv/agentsmd-lint) for AGENTS.md,
[`mcp-server-audit`](https://github.com/shriramkv/mcp-server-audit) and
[`mcp-scorecard`](https://github.com/shriramkv/mcp-scorecard) for MCP servers, and
[`goose-recipe-lint`](https://github.com/shriramkv/goose-recipe-lint) for goose. The full index is
in [`aaif-agentic-toolkit`](https://github.com/shriramkv/aaif-agentic-toolkit).

## Development

```bash
python -m unittest discover -s tests -t .
AGENT_SKILLS_LINT_NO_YAML=1 python -m unittest discover -s tests -t .   # built-in parser path
python -m agent_skills_lint check skills --min-grade A                    # dogfood
```

## License

MIT. Copyright (c) 2026 Dr. Shriram K Vasudevan.
