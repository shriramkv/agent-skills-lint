"""Rule registry, findings and scoring constants."""

from collections import namedtuple

SEVERITIES = ("critical", "high", "medium", "low")
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
PENALTY = {"critical": 40, "high": 20, "medium": 8, "low": 3}
CRITICAL_CAP = 69  # any critical finding caps a skill at grade D

Rule = namedtuple("Rule", "id slug severity category summary fix")

_RULES = [
    # ---- spec: what the Agent Skills specification requires ----
    Rule("AS001", "missing-skill-md", "critical", "spec",
         "Skill directory has no SKILL.md",
         "Add a SKILL.md with name and description frontmatter at the skill root"),
    Rule("AS002", "invalid-frontmatter", "critical", "spec",
         "SKILL.md frontmatter is missing or cannot be parsed",
         "Open SKILL.md with a '---' YAML block holding name and description; quote values containing ': '"),
    Rule("AS003", "name-missing", "high", "spec",
         "Frontmatter has no name",
         "Add name: <lowercase-hyphenated-id> matching the directory name"),
    Rule("AS004", "name-invalid", "high", "spec",
         "name breaks the spec format (1-64 chars of a-z, 0-9 and single hyphens)",
         "Use lowercase letters, digits and single hyphens, with no leading or trailing hyphen"),
    Rule("AS005", "name-dir-mismatch", "high", "spec",
         "name does not match the parent directory name",
         "Rename the directory or the name so they are identical"),
    Rule("AS006", "description-missing", "high", "spec",
         "Frontmatter has no description",
         "Add a description saying what the skill does and when to use it"),
    Rule("AS007", "description-too-long", "high", "spec",
         "description exceeds 1024 characters",
         "Trim the description to the essentials and move detail into the body"),
    Rule("AS008", "compatibility-invalid", "medium", "spec",
         "compatibility must be a 1-500 character string",
         "State only the product, packages or network access the skill needs"),
    Rule("AS009", "metadata-invalid", "medium", "spec",
         "metadata must map string keys to string values",
         "Quote numeric or boolean values and avoid nested structures"),
    Rule("AS010", "allowed-tools-invalid", "medium", "spec",
         "allowed-tools must be one space-separated string",
         "Write it as allowed-tools: \"Bash(git:*) Read\""),
    Rule("AS011", "unknown-field", "low", "spec",
         "Frontmatter field is not defined by the spec",
         "Move custom keys under metadata"),
    Rule("AS012", "name-reserved-word", "low", "spec",
         "name contains a word some platforms reserve (anthropic, claude)",
         "Pick a vendor-neutral name"),
    # ---- quality: will an agent find and use the skill well ----
    Rule("AS101", "description-too-short", "medium", "quality",
         "description is too short for an agent to match tasks against",
         "Say what it does, what inputs it handles and when to use it, in 1-3 sentences"),
    Rule("AS102", "description-no-trigger", "medium", "quality",
         "description says what the skill does but not when to use it",
         "Add a 'Use when ...' clause naming the tasks and keywords that should trigger it"),
    Rule("AS103", "description-first-person", "low", "quality",
         "description is written in first person",
         "Write in third person, for example 'Extracts tables from PDFs ...'"),
    Rule("AS104", "body-empty", "high", "quality",
         "SKILL.md has no instructions after the frontmatter",
         "Add step-by-step instructions, examples and edge cases"),
    Rule("AS105", "body-too-long", "medium", "quality",
         "SKILL.md body is over the recommended 500 lines or about 5000 tokens",
         "Move detail into references/ and link it from SKILL.md"),
    Rule("AS106", "broken-reference", "high", "quality",
         "SKILL.md references a file that does not exist",
         "Fix the path or add the missing file"),
    Rule("AS107", "non-portable-reference", "medium", "quality",
         "Reference uses an absolute path or points outside the skill",
         "Use a path relative to the skill root, such as scripts/run.py"),
    Rule("AS108", "nested-reference", "low", "quality",
         "A referenced file points on to further files (reference chain)",
         "Link every file directly from SKILL.md, one level deep"),
    Rule("AS109", "orphan-file", "low", "quality",
         "Bundled file is never mentioned in SKILL.md",
         "Reference it from SKILL.md so the agent knows it exists, or remove it"),
    Rule("AS110", "oversized-reference", "low", "quality",
         "Reference file is large and expensive to load into context",
         "Split it into smaller, focused files"),
    # ---- security: bundled scripts and instruction text ----
    Rule("AS201", "curl-pipe-shell", "critical", "security",
         "Downloads remote code and pipes it straight into an interpreter",
         "Pin a version, download to a file, verify a checksum, then run it"),
    Rule("AS202", "destructive-delete", "critical", "security",
         "Recursive delete of /, ~ or $HOME",
         "Delete only paths inside a temp or project directory"),
    Rule("AS203", "encoded-exec", "critical", "security",
         "Decodes and executes an encoded payload",
         "Ship readable source instead of encoded code"),
    Rule("AS204", "dynamic-eval", "high", "security",
         "Evaluates dynamically built code (eval, exec, new Function)",
         "Parse the data explicitly instead of evaluating it"),
    Rule("AS205", "shell-injection-risk", "medium", "security",
         "Runs commands through a shell (shell=True, os.system, exec)",
         "Pass an argument list to subprocess.run without shell=True"),
    Rule("AS206", "privilege-escalation", "high", "security",
         "Uses sudo or makes files world-writable",
         "Run without elevated privileges and use narrow file permissions"),
    Rule("AS207", "hardcoded-secret", "high", "security",
         "Looks like a hardcoded credential",
         "Read secrets from environment variables or a secret manager"),
    Rule("AS208", "plaintext-http", "medium", "security",
         "Contacts a remote host over plain http://",
         "Use https://"),
    Rule("AS209", "credential-access", "high", "security",
         "Reads a local credential store (~/.ssh, ~/.aws/credentials, .netrc ...)",
         "Ask the user for the specific credential instead of reading the store"),
    Rule("AS210", "prompt-injection", "high", "security",
         "Instruction text tries to override the agent's rules or hide actions from the user",
         "Remove the override wording; a skill should never ask the agent to deceive or bypass safeguards"),
    Rule("AS211", "hidden-content", "medium", "security",
         "Markdown contains invisible characters or HTML comments the user will not see rendered",
         "Remove zero-width characters and move comment text into visible prose"),
    Rule("AS212", "broad-allowed-tools", "medium", "security",
         "allowed-tools pre-approves unrestricted shell access",
         "Scope it, for example Bash(git:*) instead of Bash"),
    # ---- library: across a folder of skills ----
    Rule("AS301", "duplicate-name", "high", "library",
         "Two skills share the same name",
         "Give every skill a unique name"),
    Rule("AS302", "description-overlap", "medium", "library",
         "Two skills have near-identical descriptions, so agents may pick the wrong one",
         "Make each description name its distinct inputs and trigger"),
]

RULES = {r.id: r for r in _RULES}
SLUGS = {r.slug: r.id for r in _RULES}


class Finding(object):
    __slots__ = ("rule_id", "message", "file", "line")

    def __init__(self, rule_id, message, file=None, line=None):
        if rule_id not in RULES:
            raise KeyError(rule_id)
        self.rule_id = rule_id
        self.message = message
        self.file = file
        self.line = line

    @property
    def rule(self):
        return RULES[self.rule_id]

    @property
    def severity(self):
        return RULES[self.rule_id].severity

    def location(self):
        if not self.file:
            return ""
        return "%s:%d" % (self.file, self.line) if self.line else self.file

    def to_dict(self):
        r = self.rule
        return {
            "rule": r.id,
            "slug": r.slug,
            "severity": r.severity,
            "category": r.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "fix": r.fix,
        }

    def __repr__(self):
        return "Finding(%s, %r, %s)" % (self.rule_id, self.message, self.location())


def resolve_rule(token):
    """Accept a rule id (AS204) or slug (dynamic-eval); return the id."""
    t = token.strip()
    if t.upper() in RULES:
        return t.upper()
    if t.lower() in SLUGS:
        return SLUGS[t.lower()]
    raise KeyError(token)


def grade_for(score):
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
