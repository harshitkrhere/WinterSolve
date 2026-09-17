"""End-to-end tests through the Typer app, using temp projects only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from wintersolve import __version__
from wintersolve.cli import _run, app

from .conftest import write


class TestGlobalOptions:
    def test_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert result.output.strip() == f"WinterSolve {__version__}"

    def test_no_arguments_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, [])

        assert "brain" in result.output
        assert "scan" in result.output


class TestScan:
    def test_text_report(self, runner: CliRunner, python_project: Path) -> None:
        result = runner.invoke(app, ["scan", str(python_project)])

        assert result.exit_code == 0
        assert "WinterSolve Repo Scan" in result.output
        assert "Python package" in result.output

    def test_missing_directory_is_a_usage_error(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(app, ["scan", str(tmp_path / "nope")])

        assert result.exit_code == 2

    def test_json_output_is_clean_stdout(self, runner: CliRunner, python_project: Path) -> None:
        result = runner.invoke(app, ["scan", str(python_project), "--format", "json"])

        assert result.exit_code == 0
        assert json.loads(result.output)["total_files"] == 6

    def test_invalid_format_is_rejected(self, runner: CliRunner, python_project: Path) -> None:
        result = runner.invoke(app, ["scan", str(python_project), "--format", "yaml"])

        assert result.exit_code == 2

    def test_output_file(self, runner: CliRunner, python_project: Path, tmp_path: Path) -> None:
        target = tmp_path / "out" / "scan.md"
        target.parent.mkdir()

        result = runner.invoke(
            app, ["scan", str(python_project), "-f", "markdown", "--output", str(target)]
        )

        assert result.exit_code == 0
        assert "Report saved to" in result.output
        assert target.read_text(encoding="utf-8").startswith("# WinterSolve Repo Scan")


class TestBrain:
    def test_text_report(self, runner: CliRunner, python_project: Path) -> None:
        result = runner.invoke(app, ["brain", str(python_project), "--no-bandit"])

        assert result.exit_code == 0
        assert "WinterSolve Repo Brain" in result.output
        assert "Bandit skipped by request" in result.output

    def test_json_report(self, runner: CliRunner, python_project: Path) -> None:
        result = runner.invoke(app, ["brain", str(python_project), "-f", "json", "--no-bandit"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["schema_version"] == 1
        assert data["identity"]["exists"] is True

    def test_empty_directory_exits_zero(self, runner: CliRunner, empty_project: Path) -> None:
        result = runner.invoke(app, ["brain", str(empty_project), "--no-bandit"])

        assert result.exit_code == 0
        assert "No files were found in the project directory." in result.output

    def test_bracketed_paths_are_printed_literally(
        self, runner: CliRunner, node_project: Path
    ) -> None:
        # Rich markup would otherwise eat "[id]" from Next.js dynamic routes.
        result = runner.invoke(app, ["brain", str(node_project), "--no-bandit"])

        assert "app/users/[id]/page.tsx" in result.output


class TestExplain:
    def test_explains_a_file(self, runner: CliRunner, python_project: Path) -> None:
        target = python_project / "src" / "demo" / "core.py"

        result = runner.invoke(app, ["explain", str(target), "--project", str(python_project)])

        assert result.exit_code == 0
        assert "WinterSolve File Explanation" in result.output
        assert "class Demo" in result.output

    def test_refuses_files_outside_the_project(
        self, runner: CliRunner, python_project: Path
    ) -> None:
        readme = python_project / "README.md"
        source_root = python_project / "src"

        result = runner.invoke(app, ["explain", str(readme), "--project", str(source_root)])

        assert result.exit_code == 2
        assert "outside the project" in result.output


class TestDebug:
    def test_from_text(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["debug", "--text", "ModuleNotFoundError: No module named 'x'"])

        assert result.exit_code == 0
        assert "Python dependency or import path issue" in result.output

    def test_from_file(self, runner: CliRunner, tmp_path: Path) -> None:
        log = write(tmp_path / "err.log", "KeyError: 'missing'\n")

        result = runner.invoke(app, ["debug", "--file", str(log)])

        assert result.exit_code == 0
        assert "Missing dictionary key or configuration value" in result.output

    def test_from_piped_stdin(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["debug"], input="Error: listen EADDRINUSE :::8080\n")

        assert result.exit_code == 0
        assert "Source: stdin" in result.output
        assert "Port is already in use" in result.output

    def test_empty_stdin_is_a_usage_error(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["debug"], input="")

        assert result.exit_code == 2
        assert "Nothing to analyze" in result.output

    def test_text_and_file_together_is_a_usage_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        log = write(tmp_path / "err.log", "x")

        result = runner.invoke(app, ["debug", "--text", "x", "--file", str(log)])

        assert result.exit_code == 2

    def test_interactive_terminal_without_input_explains_usage(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("wintersolve.cli._stdin_is_interactive", lambda: True)

        result = runner.invoke(app, ["debug"])

        assert result.exit_code == 2
        assert "Provide --text, --file, or pipe" in result.output


class TestRunHelper:
    def test_exit_requests_pass_through_untouched(self) -> None:
        # Regression: typer.Exit is a RuntimeError, so a bare ``except Exception``
        # used to swallow it and report "Error:" with exit code 1.
        def request_exit() -> None:
            raise typer.Exit(code=2)

        with pytest.raises(typer.Exit) as raised:
            _run(request_exit)

        assert raised.value.exit_code == 2

    def test_unexpected_failures_become_exit_code_one(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def explode() -> None:
            raise RuntimeError("disk on fire")

        with pytest.raises(typer.Exit) as raised:
            _run(explode)

        assert raised.value.exit_code == 1
        assert "disk on fire" in capsys.readouterr().err


class TestDocsReviewWorkflows:
    def test_docs_with_draft(self, runner: CliRunner, python_project: Path) -> None:
        result = runner.invoke(app, ["docs", str(python_project), "--draft-readme"])

        assert result.exit_code == 0
        assert "WinterSolve Docs Assistant" in result.output
        assert "README Draft:" in result.output

    def test_review_outside_git_exits_two(self, runner: CliRunner, empty_project: Path) -> None:
        result = runner.invoke(app, ["review", str(empty_project)])

        assert result.exit_code == 2
        assert "not a Git repository" in result.output

    def test_workflows_table(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["workflows"])

        assert result.exit_code == 0
        for name in ("brain", "scan", "explain", "debug", "docs", "review"):
            assert name in result.output
