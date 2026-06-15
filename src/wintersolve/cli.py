from __future__ import annotations

import argparse
from pathlib import Path

from wintersolve import __version__
from wintersolve.modules.brain import build_brain_report
from wintersolve.modules.debugger import analyze_error_file, analyze_error_text
from wintersolve.modules.docs_assistant import suggest_docs
from wintersolve.modules.explainer import explain_file
from wintersolve.modules.reviewer import review_changes
from wintersolve.modules.scanner import scan_project
from wintersolve.project import resolve_project_path
from wintersolve.report import (
    render_brain_report,
    render_debug_analysis,
    render_docs_suggestions,
    render_explanation,
    render_review_result,
    render_scan_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wintersolve",
        description="Developer + AI toolkit for practical engineering workflows.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"WinterSolve {__version__}",
    )

    subcommands = parser.add_subparsers(dest="command")

    scan = subcommands.add_parser(
        "scan",
        help="Inspect a repository and generate a practical health report.",
    )
    scan.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project directory to scan. Defaults to the current directory.",
    )
    scan.add_argument(
        "--format",
        choices=["text", "markdown"],
        default="text",
        help="Output format.",
    )

    brain = subcommands.add_parser(
        "brain",
        help="Build a full project intelligence report.",
    )
    brain.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project directory to analyze. Defaults to the current directory.",
    )
    brain.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format.",
    )
    brain.add_argument(
        "--output",
        help="Optional file path to save the report.",
    )

    explain = subcommands.add_parser(
        "explain",
        help="Explain a source file with offline static analysis.",
    )
    explain.add_argument("file", help="File to explain.")
    explain.add_argument(
        "--project",
        default=".",
        help="Project root used to keep file access scoped. Defaults to current directory.",
    )

    debug = subcommands.add_parser(
        "debug",
        help="Analyze an error message, log file, or stack trace.",
    )
    debug_input = debug.add_mutually_exclusive_group(required=True)
    debug_input.add_argument("--text", help="Error text to analyze.")
    debug_input.add_argument("--file", help="File containing error output.")

    docs = subcommands.add_parser(
        "docs",
        help="Suggest documentation improvements for a project.",
    )
    docs.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project directory to inspect. Defaults to the current directory.",
    )
    docs.add_argument(
        "--draft-readme",
        action="store_true",
        help="Include a starter README draft in the output.",
    )

    review = subcommands.add_parser(
        "review",
        help="Review local Git changes and produce a checklist.",
    )
    review.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Git repository to review. Defaults to the current directory.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        target = Path(args.path).expanduser().resolve()
        result = scan_project(target)
        print(render_scan_report(result, output_format=args.format))
        return 0 if result.exists else 2

    if args.command == "brain":
        target = Path(args.path).expanduser().resolve()
        result = build_brain_report(target)
        output = render_brain_report(result, output_format=args.format)
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
            output_path.write_text(output + "\n", encoding="utf-8")
            print(f"WinterSolve Repo Brain report saved to {output_path}")
        else:
            print(output)
        return 0 if result.identity.exists else 2

    if args.command == "explain":
        project = Path(args.project).expanduser().resolve()
        target = resolve_project_path(project, args.file)
        print(render_explanation(explain_file(target)))
        return 0

    if args.command == "debug":
        if args.file:
            print(render_debug_analysis(analyze_error_file(Path(args.file).expanduser().resolve())))
        else:
            print(render_debug_analysis(analyze_error_text(args.text)))
        return 0

    if args.command == "docs":
        target = Path(args.path).expanduser().resolve()
        print(render_docs_suggestions(suggest_docs(target), include_draft=args.draft_readme))
        return 0

    if args.command == "review":
        target = Path(args.path).expanduser().resolve()
        print(render_review_result(review_changes(target)))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
