"""Command line interface."""

import argparse
import os
import sys

from . import __version__
from .engine import lint_paths
from .report import RENDERERS, render_rules
from .rules import GRADE_ORDER, SEVERITY_RANK, resolve_rule

SUBCOMMANDS = ("check", "rules", "demo", "version")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")


def _build_parser():
    p = argparse.ArgumentParser(
        prog="agent-skills-lint",
        description="Lint, grade and security-check Agent Skills (SKILL.md) folders.")
    sub = p.add_subparsers(dest="command")

    c = sub.add_parser("check", help="lint one skill or a folder of skills")
    c.add_argument("paths", nargs="+", help="skill directory, SKILL.md file, or folder of skills")
    _add_output_args(c)
    c.add_argument("--min-grade", choices=["A", "B", "C", "D", "F"],
                   help="exit 1 if the overall grade is below this")
    c.add_argument("--fail-on", choices=["critical", "high", "medium", "low"],
                   help="exit 1 if any finding is at or above this severity")
    c.add_argument("--disable", default="",
                   help="comma-separated rule ids or slugs to skip, e.g. AS109,orphan-file")
    c.add_argument("--overlap", type=float, default=0.6,
                   help="description similarity (0-1) that triggers AS302; 0 turns it off (default 0.6)")
    c.add_argument("--no-yaml", action="store_true",
                   help="use the built-in frontmatter parser even if PyYAML is installed")

    r = sub.add_parser("rules", help="list every rule")
    r.add_argument("--format", choices=["console", "json", "markdown"], default="console")

    d = sub.add_parser("demo", help="lint the bundled good and risky sample skills")
    _add_output_args(d)

    sub.add_parser("version", help="print the version")
    return p


def _add_output_args(p):
    p.add_argument("--format", choices=sorted(RENDERERS), default="console")
    p.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    p.add_argument("-q", "--quiet", action="store_true", help="console: summary lines only")


def _emit(report, args):
    if args.format == "console":
        text = RENDERERS["console"](report, verbose=not args.quiet)
    else:
        text = RENDERERS[args.format](report)
    if args.output:
        with open(args.output, "w") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        argv.insert(0, "check")
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    if args.command is None:
        parser.print_help()
        return 2
    if args.command == "version":
        print("agent-skills-lint %s" % __version__)
        return 0
    if args.command == "rules":
        sys.stdout.write(render_rules(args.format))
        return 0
    if args.command == "demo":
        report = lint_paths([SAMPLES_DIR])
        _emit(report, args)
        return 0

    for p in args.paths:
        if not os.path.exists(p):
            sys.stderr.write("agent-skills-lint: path not found: %s\n" % p)
            return 2
    try:
        disabled = {resolve_rule(t) for t in args.disable.split(",") if t.strip()}
    except KeyError as exc:
        sys.stderr.write("agent-skills-lint: unknown rule %s\n" % exc)
        return 2

    report = lint_paths(args.paths, disabled=disabled, overlap=args.overlap,
                        use_yaml=False if args.no_yaml else None)
    _emit(report, args)

    failed = False
    if args.min_grade and GRADE_ORDER[report.grade] < GRADE_ORDER[args.min_grade]:
        sys.stderr.write("agent-skills-lint: overall grade %s is below --min-grade %s\n"
                         % (report.grade, args.min_grade))
        failed = True
    if args.fail_on:
        worst = report.worst_severity()
        if worst and SEVERITY_RANK[worst] >= SEVERITY_RANK[args.fail_on]:
            sys.stderr.write("agent-skills-lint: found %s findings (--fail-on %s)\n"
                             % (worst, args.fail_on))
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
