"""Command-line interface for WinterSolve.

Each command does three things and nothing more: collect input, call one
analyzer, and hand the result to a renderer. Analysis logic lives in
``wintersolve.modules``; output formatting lives in ``wintersolve.report``.

Exit codes:
    0  success
    1  the analysis itself failed (unexpected error, unreadable input)
    2  invalid usage, or the target could not be analyzed (missing path, no Git)
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Annotated, NoReturn, TypeVar

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from wintersolve import __version__, configure_logging, get_logger
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
from wintersolve.workflows.registry import get_workflows

logger = get_logger("wintersolve.cli")

EXIT_FAILURE = 1
EXIT_USAGE = 2

app = typer.Typer(
    name="wintersolve",
    help="Offline-first repository intelligence: understand, debug, document, and review code.",
    epilog="Docs and examples: https://github.com/harshitkrhere/WinterSolve",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()
error_console = Console(stderr=True)

T = TypeVar("T")


class ReportFormat(str, Enum):
    text = "text"
    markdown = "markdown"
    json = "json"


# Reusable argument definitions so every command validates paths the same way.
ProjectArgument = Annotated[
    Path,
    typer.Argument(
        help="Project directory to analyze.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
    ),
]


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"WinterSolve {__version__}")
        raise typer.Exit()


@app.callback()
def _configure(
    version: Annotated[  # noqa: ARG001 - handled eagerly by _version_callback
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show debug logging on stderr."),
    ] = False,
) -> None:
    """WinterSolve: understand any repository from the terminal, no account required."""
    if verbose:
        configure_logging(level=logging.DEBUG)


def main() -> None:
    """Console script entry point (``wintersolve`` and ``python -m wintersolve``)."""
    app()


# ------------------------------------------------------------------------ commands


@app.command()
def scan(
    path: ProjectArgument = Path(),
    output_format: Annotated[
        ReportFormat,
        typer.Option("--format", "-f", help="Output format.", case_sensitive=False),
    ] = ReportFormat.text,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write the report to this file instead of stdout."),
    ] = None,
) -> None:
    """Quick repository health check: languages, stack, layout, and hygiene gaps."""
    result = _run(lambda: scan_project(path))
    _emit(
        render_scan_report(result, output_format=output_format.value), output_format.value, output
    )


@app.command()
def brain(
    path: ProjectArgument = Path(),
    output_format: Annotated[
        ReportFormat,
        typer.Option("--format", "-f", help="Output format.", case_sensitive=False),
    ] = ReportFormat.text,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write the report to this file instead of stdout."),
    ] = None,
    no_bandit: Annotated[
        bool,
        typer.Option("--no-bandit", help="Skip the optional Bandit pass (faster on large repos)."),
    ] = False,
) -> None:
    """Full project intelligence report: architecture, commands, security, risks, next steps."""
    result = _run(lambda: build_brain_report(path, run_bandit=not no_bandit))
    _emit(
        render_brain_report(result, output_format=output_format.value), output_format.value, output
    )


@app.command()
def explain(
    file: Annotated[
        Path,
        typer.Argument(
            help="File to explain.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Project root; files outside it are refused.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path(),
) -> None:
    """Explain one file: what it is, what it defines, and what it depends on."""
    try:
        target = resolve_project_path(project, str(file))
    except ValueError as error:
        _usage_error(str(error))
    result = _run(lambda: explain_file(target))
    _emit(render_explanation(result))


@app.command()
def debug(
    text: Annotated[
        str | None,
        typer.Option("--text", "-t", help="Error text to analyze.", rich_help_panel="Input"),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option(
            "--file",
            help="File containing the error output.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            rich_help_panel="Input",
        ),
    ] = None,
) -> None:
    """Analyze an error message, log, or stack trace. Reads stdin when piped."""
    if text is not None and file is not None:
        _usage_error("Provide only one of --text or --file.")

    if file is not None:
        result = _run(lambda: analyze_error_file(file))
    elif text is not None:
        result = _run(lambda: analyze_error_text(text))
    elif not _stdin_is_interactive():
        piped = sys.stdin.read()
        if not piped.strip():
            _usage_error("Nothing to analyze: stdin was empty.")
        result = _run(lambda: analyze_error_text(piped, source="stdin"))
    else:
        _usage_error("Provide --text, --file, or pipe error output into the command.")

    _emit(render_debug_analysis(result))


@app.command()
def docs(
    path: ProjectArgument = Path(),
    draft_readme: Annotated[
        bool,
        typer.Option("--draft-readme", help="Include a starter README draft in the output."),
    ] = False,
) -> None:
    """Find missing README sections and hygiene files; optionally draft a README."""
    result = _run(lambda: suggest_docs(path))
    _emit(render_docs_suggestions(result, include_draft=draft_readme))


@app.command()
def review(path: ProjectArgument = Path()) -> None:
    """Turn uncommitted Git changes into review risks and a pre-PR checklist."""
    result = _run(lambda: review_changes(path))
    _emit(render_review_result(result))
    if not result.git_available:
        raise typer.Exit(code=EXIT_USAGE)


@app.command()
def workflows() -> None:
    """List available workflows and their output formats."""
    table = Table(title="WinterSolve Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Summary", style="white")
    table.add_column("Offline", justify="center")
    table.add_column("Output Formats", style="green")
    for workflow in get_workflows():
        table.add_row(
            workflow.name,
            workflow.summary,
            "yes" if workflow.offline else "no",
            ", ".join(workflow.output_formats),
        )
    console.print(table)


# ------------------------------------------------------------------------- helpers


def _run(operation: Callable[[], T]) -> T:
    """Run an analyzer and turn unexpected failures into a clean exit code 1.

    ``typer.Exit`` is deliberately *not* caught here: it is how commands signal
    a non-zero exit, and swallowing it would turn every exit into "Error:".
    """
    try:
        return operation()
    except typer.Exit:
        raise
    except Exception as error:  # The CLI boundary reports failures; it never shows tracebacks.
        logger.debug("Command failed", exc_info=error)
        error_console.print(f"[red]Error:[/red] {escape(str(error))}")
        raise typer.Exit(code=EXIT_FAILURE) from None


def _stdin_is_interactive() -> bool:
    """True when stdin is a terminal rather than a pipe or file."""
    return sys.stdin.isatty()


def _usage_error(message: str) -> NoReturn:
    error_console.print(f"[red]Error:[/red] {escape(message)}")
    raise typer.Exit(code=EXIT_USAGE)


def _emit(rendered: str, output_format: str = "text", output: Path | None = None) -> None:
    """Print a report, or save it when ``--output`` was given.

    Reports are printed as plain text: Rich markup and emoji codes are turned
    off so a file called ``[id].tsx`` or a line containing ``:tada:`` comes out
    exactly as written. JSON bypasses Rich entirely so it is safe to pipe.
    """
    if output is not None:
        output.write_text(rendered + "\n", encoding="utf-8")
        console.print(f"[green]Report saved to[/green] {escape(str(output))}")
        return
    if output_format == "json":
        sys.stdout.write(rendered + "\n")
        return
    console.print(rendered, markup=False, highlight=False, emoji=False, soft_wrap=True)


if __name__ == "__main__":
    main()
