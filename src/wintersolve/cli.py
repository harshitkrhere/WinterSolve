from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
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

app = typer.Typer(
    name="wintersolve",
    help="Developer + AI toolkit for practical engineering workflows.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"WinterSolve {__version__}")
        raise typer.Exit()


@app.callback()
def _configure(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging."),
    ] = False,
) -> None:
    """WinterSolve - Developer + AI toolkit for practical engineering workflows."""
    if verbose:
        configure_logging(level=logging.DEBUG)


def main() -> None:
    """Console script entry point."""
    app()


@app.command()
def scan(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to scan.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path(),
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: text or markdown.",
            case_sensitive=False,
        ),
    ] = "text",
) -> None:
    """Inspect a repository and generate a practical health report."""
    try:
        scan_res = scan_project(path)
        output = render_scan_report(scan_res, output_format=format)
        console.print(output)
        if not scan_res.exists:
            raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def brain(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to analyze.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path(),
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: text, markdown, or json.",
            case_sensitive=False,
        ),
    ] = "text",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional file path to save the report.",
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Build a full project intelligence report (Repo Brain)."""
    try:
        brain_res = build_brain_report(path)
        rendered = render_brain_report(brain_res, output_format=format)

        if output:
            output.write_text(rendered + "\n", encoding="utf-8")
            console.print(f"[green]Report saved to[/green] {output}")
        elif format == "json":
            # Print raw JSON to stdout without Rich formatting
            sys.stdout.write(rendered + "\n")
        else:
            console.print(rendered)

        if not brain_res.identity.exists:
            raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None


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
            help="Project root used to keep file access scoped.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path(),
) -> None:
    """Explain a source file with offline static analysis."""
    try:
        target = resolve_project_path(project, str(file))
        explain_res = explain_file(target)
        console.print(render_explanation(explain_res))
        if not explain_res.exists:
            raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None


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
            help="File containing error output.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            rich_help_panel="Input",
        ),
    ] = None,
) -> None:
    """Analyze an error message, log file, or stack trace."""
    if text is None and file is None:
        console.print("[red]Error:[/red] Either --text or --file must be provided.")
        raise typer.Exit(code=1)
    if text is not None and file is not None:
        console.print("[red]Error:[/red] Provide only one of --text or --file.")
        raise typer.Exit(code=1)

    try:
        if file:
            result = analyze_error_file(file)
        else:
            result = analyze_error_text(text or "")
        console.print(render_debug_analysis(result))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def docs(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to inspect.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path(),
    draft_readme: Annotated[
        bool,
        typer.Option("--draft-readme", help="Include a starter README draft in the output."),
    ] = False,
) -> None:
    """Suggest documentation improvements for a project."""
    try:
        result = suggest_docs(path)
        console.print(render_docs_suggestions(result, include_draft=draft_readme))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def review(
    path: Annotated[
        Path,
        typer.Argument(
            help="Git repository to review.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path(),
) -> None:
    """Review local Git changes and produce a checklist."""
    try:
        review_res = review_changes(path)
        console.print(render_review_result(review_res))
        if not review_res.git_available:
            raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def workflows() -> None:
    """List available workflows and their output formats."""

    table = Table(title="WinterSolve Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Summary", style="white")
    table.add_column("Offline", justify="center")
    table.add_column("Output Formats", style="green")

    for wf in get_workflows():
        table.add_row(wf.name, wf.summary, "✓" if wf.offline else "✗", ", ".join(wf.output_formats))

    console.print(table)


if __name__ == "__main__":
    main()
