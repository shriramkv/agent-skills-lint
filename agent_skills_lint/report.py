"""Output renderers: console, json, markdown, badge."""

import json

from . import __version__
from .rules import RULES, SEVERITIES

BADGE_COLORS = {"A": "brightgreen", "B": "green", "C": "yellow", "D": "orange", "F": "red"}
SEV_LABEL = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}


def _plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def render_console(report, verbose=True):
    out = []
    out.append("agent-skills-lint %s | %s scanned" % (__version__, _plural(len(report.skills), "skill")))
    out.append("")
    width = max([len(s.name or s.dir_name) for s in report.skills] + [10])
    for s in report.skills:
        mark = "ok  " if s.grade in ("A", "B") and not s.counts()["critical"] else "FAIL"
        out.append("%s %-*s  %s (%3d)  %s" % (mark, width, s.name or s.dir_name, s.grade, s.score, s.rel))
        if verbose:
            for f in s.findings:
                loc = f.location()
                out.append("       %-8s %s %-24s %s%s" % (
                    SEV_LABEL[f.severity], f.rule_id, f.rule.slug,
                    (loc + "  ") if loc else "", f.message))
                out.append("                fix: %s" % f.rule.fix)
        if s.findings and verbose:
            out.append("")
    c = report.counts()
    out.append("")
    out.append("Findings: %d critical, %d high, %d medium, %d low"
               % (c["critical"], c["high"], c["medium"], c["low"]))
    out.append("Overall: %s (%d) worst-of across skills; mean score %.1f"
               % (report.grade, report.score, report.mean))
    return "\n".join(out) + "\n"


def to_dict(report):
    return {
        "tool": "agent-skills-lint",
        "version": __version__,
        "overall": {"score": report.score, "grade": report.grade, "mean": report.mean,
                    "skills": len(report.skills), "counts": report.counts()},
        "skills": [s.to_dict() for s in report.skills],
    }


def render_json(report):
    return json.dumps(to_dict(report), indent=2) + "\n"


def badge_url(report):
    msg = "%s%%20%%28%d%%29" % (report.grade, report.score)
    return "https://img.shields.io/badge/agent%%20skills-%s-%s" % (msg, BADGE_COLORS[report.grade])


def render_badge(report):
    return json.dumps({
        "schemaVersion": 1,
        "label": "agent skills",
        "message": "%s (%d)" % (report.grade, report.score),
        "color": BADGE_COLORS[report.grade],
    }) + "\n"


def _md_escape(text):
    return str(text).replace("|", "\\|")


def render_markdown(report):
    out = []
    out.append("## agent-skills-lint report")
    out.append("")
    out.append("![agent skills](%s)" % badge_url(report))
    out.append("")
    c = report.counts()
    out.append("**Overall: %s (%d)** across %s (mean %.1f). Findings: %d critical, %d high, "
               "%d medium, %d low." % (report.grade, report.score, _plural(len(report.skills), "skill"),
                                       report.mean, c["critical"], c["high"], c["medium"], c["low"]))
    out.append("")
    out.append("| Skill | Path | Grade | Score | Critical | High | Medium | Low |")
    out.append("|---|---|---|---|---|---|---|---|")
    for s in report.skills:
        k = s.counts()
        out.append("| %s | `%s` | %s | %d | %d | %d | %d | %d |" % (
            _md_escape(s.name or s.dir_name), s.rel, s.grade, s.score,
            k["critical"], k["high"], k["medium"], k["low"]))
    for s in report.skills:
        if not s.findings:
            continue
        out.append("")
        out.append("### %s (%s, %d)" % (_md_escape(s.name or s.dir_name), s.grade, s.score))
        out.append("")
        out.append("| Severity | Rule | Location | Finding | Fix |")
        out.append("|---|---|---|---|---|")
        for f in s.findings:
            out.append("| %s | %s `%s` | %s | %s | %s |" % (
                f.severity, f.rule_id, f.rule.slug,
                ("`%s`" % f.location()) if f.location() else "",
                _md_escape(f.message), _md_escape(f.rule.fix)))
    return "\n".join(out) + "\n"


def render_rules(fmt="console"):
    rules = sorted(RULES.values(), key=lambda r: r.id)
    if fmt == "json":
        return json.dumps([r._asdict() for r in rules], indent=2) + "\n"
    if fmt == "markdown":
        out = ["| Rule | Slug | Severity | Category | Checks | Fix |", "|---|---|---|---|---|---|"]
        for r in rules:
            out.append("| %s | `%s` | %s | %s | %s | %s |" % (
                r.id, r.slug, r.severity, r.category, _md_escape(r.summary), _md_escape(r.fix)))
        return "\n".join(out) + "\n"
    out = []
    for cat in ("spec", "quality", "security", "library"):
        out.append("[%s]" % cat)
        for r in rules:
            if r.category == cat:
                out.append("  %s %-26s %-8s %s" % (r.id, r.slug, r.severity, r.summary))
        out.append("")
    return "\n".join(out)


RENDERERS = {
    "console": render_console,
    "json": render_json,
    "markdown": render_markdown,
    "badge": render_badge,
}

__all__ = ["RENDERERS", "render_rules", "badge_url", "to_dict", "SEVERITIES"]
