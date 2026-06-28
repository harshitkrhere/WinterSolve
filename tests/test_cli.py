"""CLI integration tests for WinterSolve."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from wintersolve.cli import app
from wintersolve.providers import AnthropicConfig, OpenAIConfig, create_provider

runner = CliRunner()

SCAN_NOT_FOUND_EXIT = 2


class TestCLIVersion:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "WinterSolve" in result.output


class TestCLIScan:
    def test_scan_current_directory(self) -> None:
        result = runner.invoke(app, ["scan", "."])
        assert result.exit_code == 0
        assert "WinterSolve Repo Scan" in result.output

    def test_scan_missing_directory(self) -> None:
        result = runner.invoke(app, ["scan", "definitely-not-a-real-path"])
        assert result.exit_code == SCAN_NOT_FOUND_EXIT

    def test_scan_markdown_format(self) -> None:
        result = runner.invoke(app, ["scan", ".", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# WinterSolve Repo Scan" in result.output


class TestCLIBrain:
    def test_brain_current_directory(self) -> None:
        result = runner.invoke(app, ["brain", "."])
        assert result.exit_code == 0
        assert "WinterSolve Repo Brain" in result.output

    def test_brain_json_format(self) -> None:
        result = runner.invoke(app, ["brain", ".", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "identity" in data
        assert "security" in data
        assert "commands" in data

    def test_brain_output_file(self) -> None:
        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "brain-report.json"
            result = runner.invoke(
                app,
                [
                    "brain",
                    ".",
                    "--format",
                    "json",
                    "--output",
                    str(output_path),
                ],
            )
            assert result.exit_code == 0
            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert "identity" in data


class TestCLIExplain:
    def test_explain_existing_file(self) -> None:
        result = runner.invoke(app, ["explain", "src/wintersolve/cli.py"])
        assert result.exit_code == 0
        assert "WinterSolve File Explanation" in result.output
        assert "cli.py" in result.output


class TestCLIDebug:
    def test_debug_from_text(self) -> None:
        result = runner.invoke(
            app,
            ["debug", "--text", "ModuleNotFoundError: No module named 'demo'"],
        )
        assert result.exit_code == 0
        assert "WinterSolve Debug Analysis" in result.output
        assert "Python dependency" in result.output


class TestCLIDocs:
    def test_docs_current_directory(self) -> None:
        result = runner.invoke(app, ["docs", "."])
        assert result.exit_code == 0
        assert "WinterSolve Docs Assistant" in result.output


class TestCLIWorkflows:
    def test_workflows_list(self) -> None:
        result = runner.invoke(app, ["workflows"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "brain" in result.output
        assert "explain" in result.output
        assert "debug" in result.output
        assert "docs" in result.output
        assert "review" in result.output


class TestCLIReview:
    def test_review_current_directory(self) -> None:
        result = runner.invoke(app, ["review", "."])
        assert "WinterSolve Review Assistant" in result.output or "Git" in result.output


class TestCLIProviderExamples:
    def test_provider_import_works(self) -> None:
        openai_config = OpenAIConfig(name="test", model="gpt-4o", api_key="test-key")
        provider = create_provider("openai", openai_config)
        assert provider is not None

        anthropic_config = AnthropicConfig(
            name="test", model="claude-3-opus-20240229", api_key="test-key"
        )
        provider = create_provider("anthropic", anthropic_config)
        assert provider is not None
