"""SKILL.md frontmatter handling.

Uses PyYAML when it is installed, otherwise a small built-in parser that
covers the YAML subset skill frontmatter actually uses: scalars, quoted
strings, block scalars (| and >), flow lists, simple block lists and one
level of nested mapping (for ``metadata``). Set the environment variable
AGENT_SKILLS_LINT_NO_YAML=1 to force the built-in parser.
"""

import os
import re


class FrontmatterError(ValueError):
    """Raised when frontmatter is missing its closing fence or is not valid YAML."""


def split_frontmatter(text):
    """Split SKILL.md text.

    Returns (frontmatter_text, body, body_start_line). frontmatter_text is
    None when the file does not open with a '---' fence. body_start_line is
    the 1-based line number of the first body line.
    """
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r").strip() != "---":
        return None, text, 1
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r").strip() in ("---", "..."):
            fm = "\n".join(line.rstrip("\r") for line in lines[1:i])
            body = "\n".join(lines[i + 1:])
            return fm, body, i + 2
    raise FrontmatterError("frontmatter opens with '---' but is never closed")


def parse_frontmatter(fm_text, use_yaml=None):
    """Parse frontmatter text into a dict. Returns (data, parser_name)."""
    if use_yaml is None:
        use_yaml = os.environ.get("AGENT_SKILLS_LINT_NO_YAML") != "1"
    if use_yaml:
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None
        if yaml is not None:
            try:
                data = yaml.safe_load(fm_text) if fm_text.strip() else {}
            except yaml.YAMLError as exc:
                msg = " ".join(str(exc).split())
                raise FrontmatterError("YAML error: " + msg)
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise FrontmatterError("frontmatter must be a mapping of 'key: value' pairs")
            return data, "pyyaml"
    return _parse_mini(fm_text), "builtin"


_KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*)\s*:(?:\s+(.*)|\s*)$")
_CHILD_RE = re.compile(r"^(\"[^\"]*\"|'[^']*'|[^:#][^:]*?)\s*:(?:\s+(.*)|\s*)$")
_BLOCK_INDICATORS = ("|", ">", "|-", ">-", "|+", ">+")
_BOOL = {
    "true": True, "yes": True, "on": True,
    "false": False, "no": False, "off": False,
}


def _indent(line):
    return len(line) - len(line.lstrip(" \t"))


def _parse_mini(src):
    data = {}
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        lineno = i + 2  # frontmatter line 1 is the opening fence
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw[0] in " \t":
            raise FrontmatterError("line %d: unexpected indentation" % lineno)
        m = _KEY_RE.match(raw)
        if not m:
            raise FrontmatterError("line %d: expected 'key: value'" % lineno)
        key = m.group(1)
        rest = (m.group(2) or "").strip()
        if key in data:
            raise FrontmatterError("line %d: duplicate key '%s'" % (lineno, key))
        i += 1
        if rest.split(" #")[0].strip() in _BLOCK_INDICATORS:
            indicator = rest.split(" #")[0].strip()
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                block.append(lines[i])
                i += 1
            data[key] = _block_scalar(block, indicator)
        elif rest == "":
            children = []
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                if lines[i].strip() and not lines[i].strip().startswith("#"):
                    children.append((lines[i], i + 2))
                i += 1
            data[key] = _children(children)
        else:
            data[key] = _scalar(rest, lineno)
    return data


def _block_scalar(block, indicator):
    nonempty = [line for line in block if line.strip()]
    ind = min(_indent(line) for line in nonempty) if nonempty else 0
    block = [line[ind:] for line in block]
    while block and not block[-1].strip():
        block.pop()
    if indicator.startswith("|"):
        value = "\n".join(block)
    else:
        paras, cur = [], []
        for line in block:
            if line.strip():
                cur.append(line.strip())
            else:
                paras.append(" ".join(cur))
                cur = []
        paras.append(" ".join(cur))
        value = "\n".join(paras)
    if indicator in ("|", ">", "|+", ">+") and value:
        value += "\n"
    return value


def _children(children):
    if not children:
        return None
    texts = [c[0].strip() for c in children]
    if all(t == "-" or t.startswith("- ") for t in texts):
        return [_scalar(t[1:].strip(), ln) for t, (_, ln) in zip(texts, children)]
    base = _indent(children[0][0])
    mapping = {}
    last_key = None
    for raw, ln in children:
        text = raw.strip()
        if _indent(raw) > base and last_key is not None:
            m = _CHILD_RE.match(text)
            nested = mapping.get(last_key)
            if not isinstance(nested, dict):
                nested = {}
            if m:
                nested[_unquote_key(m.group(1))] = _scalar(m.group(2) or "", ln)
            mapping[last_key] = nested
            continue
        m = _CHILD_RE.match(text)
        if not m:
            raise FrontmatterError("line %d: expected 'key: value' inside a mapping" % ln)
        last_key = _unquote_key(m.group(1))
        mapping[last_key] = _scalar(m.group(2) or "", ln)
    return mapping


def _unquote_key(k):
    k = k.strip()
    if len(k) >= 2 and k[0] == k[-1] and k[0] in "\"'":
        return k[1:-1]
    return k


_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "/": "/", "r": "\r", "0": "\0"}


def _unescape(s):
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), s)


def _split_flow(inner):
    parts, cur, quote = [], [], None
    for ch in inner:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p for p in parts if p.strip()]


def _scalar(s, lineno):
    s = s.strip()
    if s == "":
        return None
    if s[0] == '"':
        m = re.match(r'^"((?:[^"\\]|\\.)*)"\s*(?:#.*)?$', s)
        if not m:
            raise FrontmatterError("line %d: unterminated or malformed double-quoted string" % lineno)
        return _unescape(m.group(1))
    if s[0] == "'":
        m = re.match(r"^'((?:[^']|'')*)'\s*(?:#.*)?$", s)
        if not m:
            raise FrontmatterError("line %d: unterminated or malformed single-quoted string" % lineno)
        return m.group(1).replace("''", "'")
    if s[0] == "[":
        body = re.sub(r"\s+#.*$", "", s)
        if not body.endswith("]"):
            raise FrontmatterError("line %d: unterminated flow list" % lineno)
        inner = body[1:-1].strip()
        return [_scalar(p, lineno) for p in _split_flow(inner)] if inner else []
    if s[0] == "{":
        if re.match(r"^\{\s*\}\s*(?:#.*)?$", s):
            return {}
        raise FrontmatterError(
            "line %d: inline {..} mappings are not supported; use an indented block" % lineno)
    s = re.sub(r"\s+#.*$", "", s)
    if s[0] in "&*!%@`":
        raise FrontmatterError(
            "line %d: a plain value cannot start with '%s'; wrap it in quotes" % (lineno, s[0]))
    if re.search(r":(\s|$)", s):
        raise FrontmatterError(
            "line %d: unquoted value contains ': ', which YAML rejects; wrap the value in quotes"
            % lineno)
    low = s.lower()
    if low in _BOOL:
        return _BOOL[low]
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"[-+]?\d+", s):
        return int(s)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?", s):
        return float(s)
    return s
