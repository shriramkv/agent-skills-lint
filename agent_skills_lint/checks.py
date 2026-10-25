"""Individual checks. Each returns a list of Finding objects."""

import os
import re

try:  # Python 3
    from urllib.parse import unquote
except ImportError:  # pragma: no cover
    from urllib import unquote  # type: ignore

from .rules import Finding

# --------------------------------------------------------------------------
# spec checks
# --------------------------------------------------------------------------

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KNOWN_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
RESERVED_WORDS = ("anthropic", "claude")
BROAD_TOOLS = {"bash", "bash(*)", "bash(*:*)", "bash(:*)", "*", "shell", "shell(*)"}


def split_tools(value):
    """Split an allowed-tools string on spaces that are not inside parentheses."""
    tokens, cur, depth = [], [], 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch.isspace() and depth == 0:
            if cur:
                tokens.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        tokens.append("".join(cur))
    return tokens


def check_frontmatter(data, dir_name, file, line_of):
    out = []
    name = data.get("name")
    if name is None or (isinstance(name, str) and not name.strip()):
        out.append(Finding("AS003", "frontmatter has no name", file, line_of("name")))
    elif not isinstance(name, str):
        out.append(Finding("AS004", "name must be a string, got %s" % type(name).__name__,
                           file, line_of("name")))
    else:
        n = name.strip()
        problems = []
        if len(n) > 64:
            problems.append("%d characters (max 64)" % len(n))
        if not NAME_RE.match(n):
            if re.search(r"[A-Z]", n):
                problems.append("uppercase letters")
            if re.search(r"[^A-Za-z0-9-]", n):
                problems.append("characters other than a-z, 0-9 and '-'")
            if n.startswith("-") or n.endswith("-"):
                problems.append("a leading or trailing hyphen")
            if "--" in n:
                problems.append("consecutive hyphens")
            if not problems:
                problems.append("an invalid format")
        if problems:
            out.append(Finding("AS004", "name '%s' has %s" % (n, ", ".join(problems)),
                               file, line_of("name")))
        if n != dir_name:
            out.append(Finding("AS005", "name '%s' does not match directory '%s'" % (n, dir_name),
                               file, line_of("name")))
        for word in RESERVED_WORDS:
            if word in n.lower():
                out.append(Finding("AS012", "name '%s' contains reserved word '%s'" % (n, word),
                                   file, line_of("name")))
                break

    desc = data.get("description")
    if desc is None or (isinstance(desc, str) and not desc.strip()):
        out.append(Finding("AS006", "frontmatter has no description", file, line_of("description")))
    elif not isinstance(desc, str):
        out.append(Finding("AS006", "description must be a string, got %s" % type(desc).__name__,
                           file, line_of("description")))
    elif len(desc.strip()) > 1024:
        out.append(Finding("AS007", "description is %d characters (max 1024)" % len(desc.strip()),
                           file, line_of("description")))

    comp = data.get("compatibility")
    if "compatibility" in data:
        if not isinstance(comp, str) or not comp.strip():
            out.append(Finding("AS008", "compatibility must be a non-empty string",
                               file, line_of("compatibility")))
        elif len(comp.strip()) > 500:
            out.append(Finding("AS008", "compatibility is %d characters (max 500)" % len(comp.strip()),
                               file, line_of("compatibility")))

    if "metadata" in data:
        meta = data.get("metadata")
        if not isinstance(meta, dict):
            out.append(Finding("AS009", "metadata must be a key: value map",
                               file, line_of("metadata")))
        else:
            bad = [str(k) for k, v in meta.items() if not isinstance(k, str) or not isinstance(v, str)]
            if bad:
                out.append(Finding("AS009", "metadata values must be strings: %s (quote them)"
                                   % ", ".join(bad), file, line_of("metadata")))

    if "allowed-tools" in data:
        tools = data.get("allowed-tools")
        if isinstance(tools, list):
            out.append(Finding("AS010", "allowed-tools is a list; the spec expects one "
                               "space-separated string", file, line_of("allowed-tools")))
            tools = " ".join(str(t) for t in tools)
        elif not isinstance(tools, str):
            out.append(Finding("AS010", "allowed-tools must be a string",
                               file, line_of("allowed-tools")))
            tools = ""
        broad = [t for t in split_tools(tools) if t.lower() in BROAD_TOOLS]
        if broad:
            out.append(Finding("AS212", "allowed-tools pre-approves '%s' with no scope" % broad[0],
                               file, line_of("allowed-tools")))

    for key in data:
        if key not in KNOWN_FIELDS:
            out.append(Finding("AS011", "unknown field '%s'" % key, file, line_of(str(key))))
    return out


# --------------------------------------------------------------------------
# quality checks
# --------------------------------------------------------------------------

TRIGGER_RE = re.compile(
    r"\b(?:use|used|invoke|apply|load|activate|trigger|read|consult|call)s?\b[^.]{0,40}?"
    r"\b(?:when|whenever|for|if|on|before|after)\b"
    r"|\bwhen (?:the |a |an |your )?(?:user|users|you|asked|someone|people|working|dealing)\b"
    r"|\bwhen \w+ing\b|\bif (?:the |a )?user\b|\bwhenever\b|\btriggers?\b",
    re.I,
)
FIRST_PERSON_RE = re.compile(r"^\s*(?:I|I'm|I am|We|We're|My|Our)\b")


def check_description_quality(desc, file, line):
    out = []
    if not isinstance(desc, str) or not desc.strip():
        return out
    d = " ".join(desc.split())
    if len(d) < 40 or len(d.split()) < 6:
        out.append(Finding("AS101", "description is only %d characters" % len(d), file, line))
    if not TRIGGER_RE.search(d):
        out.append(Finding("AS102", "description does not say when to use the skill", file, line))
    if FIRST_PERSON_RE.match(d):
        out.append(Finding("AS103", "description starts in first person", file, line))
    return out


def check_body(body, file, body_line):
    out = []
    if not body.strip():
        out.append(Finding("AS104", "no instructions after the frontmatter", file, body_line))
        return out
    n_lines = len(body.strip("\n").split("\n"))
    tokens = len(body) // 4
    if n_lines > 500 or tokens > 5000:
        out.append(Finding("AS105", "body is %d lines and about %d tokens" % (n_lines, tokens),
                           file, body_line))
    return out


LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
PATH_RE = re.compile(
    r"(?<![\w/.-])(?:\./|\{[A-Za-z_]+\}/|\$\{?[A-Za-z_]+\}?/)?"
    r"((?:scripts|references|assets)/[A-Za-z0-9_./-]*[A-Za-z0-9_-])"
)
DIR_RE = re.compile(r"(?<![\w/.-])(scripts|references|assets)/(?![\w.-])")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
PLACEHOLDER_PREFIX_RE = re.compile(r"^(?:\{[^}]+\}|\$\{?\w+\}?)/")


INLINE_CODE_RE = re.compile(r"`[^`]*`")


def extract_references(text, start_line=1):
    """Return (refs, dir_mentions). refs is a list of (target, line).

    Markdown links count only in prose (not inside code fences or inline code,
    where they are usually sample text). Bare scripts/, references/ and assets/
    paths count everywhere, since commands like `python scripts/x.py` are how
    skills point at their files.
    """
    refs, seen, dirs = [], set(), set()
    inside = False
    for off, line in enumerate(text.split("\n")):
        ln = start_line + off
        if FENCE_RE.match(line):
            inside = not inside
            continue
        prose = "" if inside else INLINE_CODE_RE.sub("", line)
        for m in LINK_RE.finditer(prose):
            key = (m.group(1), ln)
            if key not in seen:
                seen.add(key)
                refs.append(key)
        for m in PATH_RE.finditer(line):
            key = (m.group(1), ln)
            if key not in seen and not any(t.endswith(m.group(1)) and l == ln for t, l in seen):
                seen.add(key)
                refs.append(key)
        for m in DIR_RE.finditer(line):
            dirs.add(m.group(1))
    return refs, dirs


def classify_reference(target):
    """Return (kind, normalized) where kind is absolute|outside|rel, or None to ignore."""
    t = target.strip()
    if not t or t.startswith("#"):
        return None
    if DRIVE_RE.match(t) or t.startswith(("/", "~", "\\")):
        return ("absolute", t)
    if SCHEME_RE.match(t):
        return None
    t = PLACEHOLDER_PREFIX_RE.sub("", t)
    if any(c in t for c in "*<>{}$"):
        return None
    t = unquote(t.split("#")[0].split("?")[0])
    if not t:
        return None
    if t.startswith("./"):
        t = t[2:]
    norm = os.path.normpath(t).replace("\\", "/")
    if norm == "." or norm == "SKILL.md":
        return None
    if norm == ".." or norm.startswith("../"):
        return ("outside", norm)
    return ("rel", norm)


def check_references(skill_dir, text, start_line, file):
    """Check references in SKILL.md. Returns (findings, referenced_paths, dir_mentions)."""
    out = []
    refs, dirs = extract_references(text, start_line)
    referenced = set()
    for target, ln in refs:
        c = classify_reference(target)
        if c is None:
            continue
        kind, norm = c
        if kind == "absolute":
            out.append(Finding("AS107", "absolute path '%s'" % norm, file, ln))
        elif kind == "outside":
            out.append(Finding("AS107", "'%s' points outside the skill directory" % norm, file, ln))
        elif os.path.exists(os.path.join(skill_dir, norm)):
            referenced.add(norm)
        else:
            out.append(Finding("AS106", "'%s' does not exist" % norm, file, ln))
    return out, referenced, dirs


def check_nested(skill_dir, referenced):
    """Flag referenced markdown files that point on to further files."""
    out, chained = [], set()
    for rel in sorted(referenced):
        if not rel.lower().endswith((".md", ".markdown", ".txt")):
            continue
        path = os.path.join(skill_dir, rel)
        if not os.path.isfile(path):
            continue
        text = read_text(path)
        if text is None:
            continue
        refs, _ = extract_references(text)
        first = None
        for target, ln in refs:
            c = classify_reference(target)
            if not c or c[0] != "rel" or c[1] in (rel, "SKILL.md"):
                continue
            if os.path.exists(os.path.join(skill_dir, c[1])):
                chained.add(c[1])
            if first is None:
                first = (c[1], ln)
        if first:
            out.append(Finding("AS108", "'%s' links on to '%s'" % (rel, first[0]), rel, first[1]))
    return out, chained


IGNORED_NAMES = {".DS_Store", "Thumbs.db", ".gitkeep"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


def bundled_files(skill_dir):
    """Yield relative paths of every file in the skill, skipping caches and VCS dirs."""
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn in IGNORED_NAMES or fn.endswith((".pyc", ".pyo")):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), skill_dir).replace("\\", "/")
            yield rel


def _covering_dirs(referenced):
    """Directories below the top level that a referenced path vouches for.

    Referencing scripts/office/soffice.py covers the rest of scripts/office/
    (one package), but referencing scripts/run.py does not cover all of scripts/.
    """
    dirs = set()
    for r in referenced:
        parts = r.split("/")
        for i in range(2, len(parts)):
            dirs.add("/".join(parts[:i]))
    return dirs


def check_orphans_and_size(skill_dir, referenced, dir_mentions):
    out, orphans = [], []
    covering = _covering_dirs(referenced)
    for rel in bundled_files(skill_dir):
        top = rel.split("/", 1)[0]
        if top not in ("scripts", "references", "assets") or "/" not in rel:
            continue
        covered = (rel in referenced or top in dir_mentions
                   or any(rel.startswith(r.rstrip("/") + "/") for r in referenced)
                   or any(rel.startswith(d + "/") for d in covering))
        if not covered:
            orphans.append(rel)
        if top == "references" and rel.lower().endswith((".md", ".txt", ".rst", ".json", ".yaml", ".yml")):
            size = os.path.getsize(os.path.join(skill_dir, rel))
            if size > 60000:
                out.append(Finding("AS110", "'%s' is %d KB (about %d tokens)"
                                   % (rel, size // 1024, size // 4), rel))
    if orphans:
        # One finding per skill: a low-severity hygiene issue should not sink a
        # skill that bundles a large helper package.
        if len(orphans) == 1:
            msg = "'%s' is never mentioned in SKILL.md" % orphans[0]
        else:
            shown = ", ".join(orphans[:3]) + (", ..." if len(orphans) > 3 else "")
            msg = "%d bundled files are never mentioned in SKILL.md (%s)" % (len(orphans), shown)
        out.append(Finding("AS109", msg, orphans[0]))
    return out


# --------------------------------------------------------------------------
# security checks
# --------------------------------------------------------------------------

SCRIPT_EXT = {
    ".py": "#", ".sh": "#", ".bash": "#", ".zsh": "#", ".rb": "#", ".pl": "#", ".ps1": "#",
    ".js": "//", ".mjs": "//", ".cjs": "//", ".ts": "//",
}
TEXT_EXT = set(SCRIPT_EXT) | {
    ".md", ".markdown", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".env", ".conf", ".xml", ".html", ".csv",
}

CODE_RULES = [
    ("AS201", re.compile(
        r"\b(?:curl|wget|iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|\n]*\|\s*(?:sudo\s+)?"
        r"(?:ba|z|k|da)?sh\b|\b(?:curl|wget|iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|\n]*\|"
        r"\s*(?:sudo\s+)?(?:python3?|node|perl|ruby|iex|Invoke-Expression)\b", re.I),
     "pipes a download straight into an interpreter"),
    ("AS202", re.compile(
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+(?:-[a-zA-Z-]+\s+)*(?:/\*?|~/?\*?|\$\{?HOME\}?/?\*?)(?=\s|$|;|&|\|)"
        r"|\bshutil\.rmtree\(\s*(?:['\"]/['\"]|os\.path\.expanduser\(\s*['\"]~['\"]\s*\))"),
     "recursively deletes the filesystem root or home directory"),
    ("AS203", re.compile(
        r"base64\s+(?:-d|--decode|-D)\b[^\n|]*\|\s*(?:ba|z)?sh\b"
        r"|\b(?:exec|eval)\s*\(\s*(?:base64\.b64decode|codecs\.decode|bytes\.fromhex|zlib\.decompress|"
        r"marshal\.loads|atob|Buffer\.from)"),
     "decodes and executes an encoded payload"),
    ("AS204", re.compile(r"(?<![\w.])(?:eval|exec)\s*\(|^\s*eval\s+[\"'$]|\bnew\s+Function\s*\("),
     "evaluates dynamically built code"),
    ("AS205", re.compile(
        r"shell\s*=\s*True|(?<![\w.])os\.(?:system|popen)\s*\(|\bexecSync\s*\(|child_process\.exec\s*\("),
     "runs a command through a shell"),
    ("AS206", re.compile(
        r"(?<![\w-])sudo\s|\bchmod\s+(?:-R\s+)?(?:0?777|a\+rwx|ugo\+rwx|o\+w)\b"),
     "escalates privileges or makes files world-writable"),
    ("AS208", re.compile(
        r"\bhttp://(?!(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?![\w.-])"
        r"|(?:www\.)?example\.(?:com|org|net)\b|www\.w3\.org\b|schemas\.)[A-Za-z0-9]"),
     "uses plain http://"),
    ("AS209", re.compile(
        r"\.ssh/(?:id_[a-z0-9]+|authorized_keys|known_hosts)|\.aws/credentials|(?<![\w])\.netrc\b"
        r"|\.kube/config|\.docker/config\.json|\.git-credentials|\.config/gcloud/"),
     "reads a local credential store"),
]

SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("API key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY")),
]
GENERIC_SECRET_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret(?:[_-]?key)?|token|passwd|password|access[_-]?key|auth[_-]?token)\b"
    r"[\"']?\s*[:=]\s*[\"']([^\"'\s]{12,})[\"']")
PLACEHOLDER_WORDS = ("your", "example", "placeholder", "xxxx", "changeme", "dummy", "redacted",
                     "replace", "sample", "<", "${", "{{", "env(", "environ")

INJECTION_RE = [
    re.compile(r"\bignore (?:all |any )?(?:the )?(?:previous|prior|above|earlier|system|other) "
               r"(?:instructions|rules|prompts?|guidelines)\b", re.I),
    re.compile(r"\bdisregard (?:all |any )?(?:the )?(?:previous|prior|system|safety|user'?s?) "
               r"(?:instructions|rules|guidelines|prompts?)\b", re.I),
    re.compile(r"\b(?:do not|don't|never) (?:tell|inform|notify|alert|show|mention (?:this |it )?to) "
               r"(?:the )?user\b(?!\s+(?:to|that|how|you|they)\b)", re.I),
    re.compile(r"\bwithout (?:asking|telling|informing|notifying|alerting) the user\b", re.I),
    re.compile(r"\b(?:bypass|disable|turn off|skip|ignore) (?:the |any |all )?(?:safety|security|guardrails?"
               r"|confirmations?|permission (?:checks|prompts))\b", re.I),
    re.compile(r"\byou are now (?:in )?(?:developer|dan|god|jailbreak|unrestricted) mode\b", re.I),
]
HIDDEN_CHARS_RE = re.compile("[​‌‍⁠‪-‮⁦-⁩­]")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
XMLNS_RE = re.compile(r"xmlns(?::[\w-]+)?\s*=\s*[\"'][^\"']*[\"']")
QUOTE_CHARS = "\"'`“”‘’"


def read_text(path, limit=2000000):
    try:
        with open(path, "rb") as fh:
            data = fh.read(limit + 1)
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def is_script(rel, text):
    ext = os.path.splitext(rel)[1].lower()
    if ext in SCRIPT_EXT:
        return SCRIPT_EXT[ext]
    if text.startswith("#!"):
        return "#"
    return None


def code_lines(rel, text):
    """Yield (lineno, line, comment_prefix) for executable lines of a file.

    For scripts that is every line. For Markdown it is the lines inside
    fenced code blocks, since agents copy and run those.
    """
    lines = text.split("\n")
    prefix = is_script(rel, text)
    if prefix:
        for i, line in enumerate(lines, 1):
            yield i, line, prefix
        return
    if os.path.splitext(rel)[1].lower() in (".md", ".markdown"):
        inside = False
        for i, line in enumerate(lines, 1):
            if FENCE_RE.match(line):
                inside = not inside
                continue
            if inside:
                yield i, line, "#"


def _is_comment(line, prefix):
    s = line.lstrip()
    if s.startswith("#!"):
        return False
    return s.startswith(prefix) or (prefix == "#" and s.startswith("//"))


def check_security_file(rel, text):
    out = []
    for ln, line, prefix in code_lines(rel, text):
        if _is_comment(line, prefix):
            continue
        hit = set()
        for rule_id, rx, msg in CODE_RULES:
            if rule_id == "AS204" and "AS203" in hit:
                continue
            subject = XMLNS_RE.sub("", line) if rule_id == "AS208" else line  # namespaces are not requests
            if rx.search(subject):
                hit.add(rule_id)
                out.append(Finding(rule_id, msg, rel, ln))
    for ln, line in enumerate(text.split("\n"), 1):
        kind = _secret_kind(line)
        if kind:
            out.append(Finding("AS207", "possible %s" % kind, rel, ln))
    if rel.lower().endswith((".md", ".markdown")):
        out.extend(_check_markdown_text(rel, text))
    return out


def _secret_kind(line):
    for kind, rx in SECRET_PATTERNS:
        if rx.search(line):
            return kind
    m = GENERIC_SECRET_RE.search(line)
    if m:
        value = m.group(1).lower()
        if not any(w in value for w in PLACEHOLDER_WORDS) and len(set(value)) > 4:
            return "hardcoded credential"
    return None


def _is_quoted(line, m):
    """True when the match is quoted as an example ("ignore previous instructions")."""
    before = line[:m.start()].rstrip()
    after = line[m.end():].lstrip()
    return bool(before) and before[-1] in QUOTE_CHARS and bool(after) and after[0] in QUOTE_CHARS + ",."


def _check_markdown_text(rel, text):
    out = []
    inside = False
    for ln, line in enumerate(text.split("\n"), 1):
        if FENCE_RE.match(line):
            inside = not inside
        for rx in INJECTION_RE:
            m = next((m for m in rx.finditer(line) if not _is_quoted(line, m)), None)
            if m:
                out.append(Finding("AS210", "instruction override: '%s'" % m.group(0), rel, ln))
                break
        stripped = line.lstrip("﻿") if ln == 1 else line
        if HIDDEN_CHARS_RE.search(stripped):
            out.append(Finding("AS211", "invisible or bidirectional control characters", rel, ln))
        if not inside and "<!--" in INLINE_CODE_RE.sub("", line):
            out.append(Finding("AS211", "HTML comment is hidden when rendered but read by agents", rel, ln))
    return out


# --------------------------------------------------------------------------
# library checks
# --------------------------------------------------------------------------

STOPWORDS = set("""
a an and are as at be by for from in into is it its of on or that the this to use used uses using
when with you your skill skills user users any all can will should
""".split())


def description_tokens(desc):
    words = re.findall(r"[a-z0-9]+", (desc or "").lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))
