"""Discovery, per-skill linting, library checks and scoring."""

import os
import re

from . import checks
from .frontmatter import FrontmatterError, parse_frontmatter, split_frontmatter
from .rules import CRITICAL_CAP, PENALTY, SEVERITY_RANK, Finding, grade_for

SUPPRESS_RE = re.compile(r"agent-skills-lint:\s*disable(?:-line)?=([A-Za-z0-9_,\s-]+)")


class SkillResult(object):
    def __init__(self, path, rel, dir_name):
        self.path = path
        self.rel = rel
        self.dir_name = dir_name
        self.name = None
        self.description = None
        self.parser = None
        self.findings = []
        self.score = 100
        self.grade = "A"

    def rescore(self):
        total = sum(PENALTY[f.severity] for f in self.findings)
        score = max(0, 100 - total)
        if any(f.severity == "critical" for f in self.findings):
            score = min(score, CRITICAL_CAP)
        self.score = score
        self.grade = grade_for(score)

    def counts(self):
        c = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in self.findings:
            c[f.severity] += 1
        return c

    def to_dict(self):
        return {
            "name": self.name,
            "directory": self.dir_name,
            "path": self.rel,
            "score": self.score,
            "grade": self.grade,
            "counts": self.counts(),
            "findings": [f.to_dict() for f in self.findings],
        }


class Report(object):
    def __init__(self, root, skills):
        self.root = root
        self.skills = skills

    @property
    def score(self):
        return min(s.score for s in self.skills) if self.skills else 0

    @property
    def grade(self):
        return grade_for(self.score)

    @property
    def mean(self):
        if not self.skills:
            return 0.0
        return round(sum(s.score for s in self.skills) / float(len(self.skills)), 1)

    def findings(self):
        for s in self.skills:
            for f in s.findings:
                yield s, f

    def counts(self):
        c = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for _, f in self.findings():
            c[f.severity] += 1
        return c

    def worst_severity(self):
        worst = None
        for _, f in self.findings():
            if worst is None or SEVERITY_RANK[f.severity] > SEVERITY_RANK[worst]:
                worst = f.severity
        return worst


def _find_skill_md(directory):
    """Return (filename, exact) for the SKILL.md in a directory, or (None, False)."""
    try:
        names = os.listdir(directory)
    except OSError:
        return None, False
    if "SKILL.md" in names:
        return "SKILL.md", True
    for n in names:
        if n.lower() == "skill.md":
            return n, False
    return None, False


def discover(root):
    """Return a sorted list of skill directories under root."""
    root = os.path.abspath(root)
    if os.path.isfile(root):
        return [os.path.dirname(root)]
    if _find_skill_md(root)[0]:
        return [root]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in checks.SKIP_DIRS and not d.startswith("."))
        if any(f.lower() == "skill.md" for f in filenames):
            found.append(dirpath)
            dirnames[:] = []
    return sorted(found)


def lint_skill(skill_dir, base=None, use_yaml=None):
    """Lint a single skill directory. Returns a scored SkillResult."""
    result = _lint_skill(skill_dir, base, use_yaml)
    result.rescore()
    return result


def _lint_skill(skill_dir, base=None, use_yaml=None):
    skill_dir = os.path.abspath(skill_dir)
    base = base or os.path.dirname(skill_dir)
    rel = os.path.relpath(skill_dir, base).replace("\\", "/")
    result = SkillResult(skill_dir, rel, os.path.basename(skill_dir))
    out = result.findings

    md_name, exact = _find_skill_md(skill_dir)
    if md_name is None:
        out.append(Finding("AS001", "no SKILL.md in '%s'" % rel))
        return result
    if not exact:
        out.append(Finding("AS001", "found '%s'; the spec requires the exact name SKILL.md" % md_name,
                           md_name))

    text = checks.read_text(os.path.join(skill_dir, md_name)) or ""
    try:
        fm_text, body, body_line = split_frontmatter(text)
    except FrontmatterError as exc:
        out.append(Finding("AS002", str(exc), md_name, 1))
        return result
    if fm_text is None:
        out.append(Finding("AS002", "SKILL.md does not start with a '---' frontmatter block",
                           md_name, 1))
        data = {}
    else:
        try:
            data, result.parser = parse_frontmatter(fm_text, use_yaml=use_yaml)
        except FrontmatterError as exc:
            out.append(Finding("AS002", str(exc), md_name, 1))
            data = None

    lines = text.split("\n")
    fm_end = max(1, body_line - 2)

    def line_of(key):
        rx = re.compile(r"^\s*" + re.escape(key) + r"\s*:")
        for i in range(1, min(fm_end, len(lines))):
            if rx.match(lines[i]):
                return i + 1
        return None

    if data is not None and fm_text is not None:
        result.name = data.get("name") if isinstance(data.get("name"), str) else None
        result.description = data.get("description") if isinstance(data.get("description"), str) else None
        out.extend(checks.check_frontmatter(data, result.dir_name, md_name, line_of))
        out.extend(checks.check_description_quality(data.get("description"), md_name,
                                                    line_of("description")))

    out.extend(checks.check_body(body, md_name, body_line))
    ref_findings, referenced, dirs = checks.check_references(skill_dir, body, body_line, md_name)
    out.extend(ref_findings)
    nested, chained = checks.check_nested(skill_dir, referenced)
    out.extend(nested)
    out.extend(checks.check_orphans_and_size(skill_dir, referenced | chained, dirs))

    for frel in checks.bundled_files(skill_dir):
        ext = os.path.splitext(frel)[1].lower()
        path = os.path.join(skill_dir, frel)
        if ext not in checks.TEXT_EXT and frel != md_name:
            head = checks.read_text(path, limit=64)
            if not head or not head.startswith("#!"):
                continue
        ftext = text if frel == md_name else checks.read_text(path)
        if ftext is None:
            continue
        out.extend(checks.check_security_file(frel, ftext))
    return result


def _apply_suppressions(result, disabled):
    cache = {}
    kept = []
    for f in result.findings:
        if f.rule_id in disabled:
            continue
        if f.file and f.line:
            if f.file not in cache:
                cache[f.file] = (checks.read_text(os.path.join(result.path, f.file)) or "").split("\n")
            lines = cache[f.file]
            if 0 < f.line <= len(lines):
                m = SUPPRESS_RE.search(lines[f.line - 1])
                if m:
                    ids = {t.strip().upper() for t in m.group(1).split(",") if t.strip()}
                    if "ALL" in ids or f.rule_id in ids:
                        continue
        kept.append(f)
    result.findings = kept


def _library_checks(results, overlap):
    by_name = {}
    for r in results:
        if r.name:
            by_name.setdefault(r.name.strip(), []).append(r)
    for name, group in sorted(by_name.items()):
        if len(group) > 1:
            for r in group:
                others = ", ".join(o.rel for o in group if o is not r)
                r.findings.append(Finding("AS301", "name '%s' is also used by %s" % (name, others),
                                          "SKILL.md"))
    if overlap <= 0:
        return
    toks = [(r, checks.description_tokens(r.description)) for r in results if r.description]
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, ta = toks[i]
            b, tb = toks[j]
            sim = checks.jaccard(ta, tb)
            if sim >= overlap:
                b.findings.append(Finding(
                    "AS302", "description overlaps %d%% with '%s'" % (int(sim * 100), a.rel),
                    "SKILL.md"))


def lint_paths(paths, disabled=(), overlap=0.6, use_yaml=None):
    """Lint one or more paths. Returns a Report."""
    disabled = set(disabled)
    results = []
    roots = [os.path.abspath(p) for p in paths]
    for root in roots:
        skill_dirs = discover(root)
        if not skill_dirs:
            r = SkillResult(root, os.path.basename(root) or root, os.path.basename(root))
            r.findings.append(Finding("AS001", "no SKILL.md found under '%s'" % root))
            results.append(r)
            continue
        base = os.path.dirname(root) if root in skill_dirs else root
        for d in skill_dirs:
            results.append(lint_skill(d, base=base, use_yaml=use_yaml))
    _library_checks(results, overlap)
    for r in results:
        _apply_suppressions(r, disabled)
        r.findings.sort(key=lambda f: (-SEVERITY_RANK[f.severity], f.file or "", f.line or 0, f.rule_id))
        r.rescore()
    return Report(roots[0] if len(roots) == 1 else os.getcwd(), results)
