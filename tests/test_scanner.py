from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from wintersolve.modules.brain import build_brain_report
from wintersolve.modules.command_detector import detect_commands
from wintersolve.modules.debugger import analyze_error_text
from wintersolve.modules.docs_assistant import suggest_docs
from wintersolve.modules.explainer import explain_file
from wintersolve.modules.scanner import scan_project
from wintersolve.modules.security import analyze_security, redact_secrets
from wintersolve.project import resolve_project_path
from wintersolve.report import render_brain_report, render_scan_report


class TestScanner:
    def test_scan_detects_python_project_health_signals(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "demo.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_demo.py").write_text(
                "def test_demo(): pass\n", encoding="utf-8"
            )

            result = scan_project(root)

        assert result.exists
        assert ("Python", 2) in result.languages
        assert "Python package" in result.frameworks
        assert "README.md" in result.important_files
        assert "tests" in result.likely_test_paths

    def test_scan_reports_missing_directory(self) -> None:
        result = scan_project(Path("definitely-missing-directory").resolve())

        assert not result.exists
        assert result.total_files == 0
        assert result.risks

    def test_markdown_report_renders_recommendations(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            result = scan_project(root)

        report = render_scan_report(result, output_format="markdown")

        assert "# WinterSolve Repo Scan" in report
        assert "## Recommendations" in report


class TestExplainer:
    def test_explain_file_detects_python_symbols(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "demo.py"
            target.write_text("import os\n\nclass Demo:\n    pass\n", encoding="utf-8")

            result = explain_file(target)

        assert result.language == "Python"
        assert "class Demo" in result.symbols
        assert "os" in result.imports


class TestDebugger:
    def test_debugger_detects_missing_python_module(self) -> None:
        result = analyze_error_text("ModuleNotFoundError: No module named 'demo'")

        assert result.likely_language == "Python"
        assert "Python dependency or import path issue" in result.likely_causes
        assert "DNS, host, or network configuration issue" not in result.likely_causes


class TestDocsAssistant:
    def test_docs_assistant_suggests_missing_sections(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            result = suggest_docs(root)

        assert "Installation" in result.missing_sections
        assert "# Demo" in result.readme_draft


class TestBrainReport:
    def test_brain_report_generates_json_shape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n\n## Usage\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "demo.py").write_text("print('hello')\n", encoding="utf-8")

            report = build_brain_report(root)
            rendered = render_brain_report(report, output_format="json")

        assert '"identity"' in rendered
        assert '"security"' in rendered
        assert '"commands"' in rendered

    def test_brain_report_handles_empty_repo(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_brain_report(root)

        assert report.identity.exists
        assert "No files were found in the project directory." in report.risks

    def test_brain_report_detects_mixed_python_node_repo(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Mixed\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'mixed'\n", encoding="utf-8")
            (root / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "src" / "app.ts").write_text("console.log('hi')\n", encoding="utf-8")

            report = build_brain_report(root)

        assert "Python package" in report.stack
        assert "Node.js" in report.stack
        assert ("Python", 1) in report.languages
        assert ("TypeScript", 1) in report.languages


class TestCommandDetector:
    def test_command_detector_reads_package_scripts(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                '{"scripts":{"dev":"vite","test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )

            commands = detect_commands(root)

        assert "npm run dev" in [command.command for command in commands]
        assert "npm run test" in [command.command for command in commands]


class TestSecurity:
    def test_security_redacts_secret_like_values(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            secret_line = "API_" + "KEY=" + "1234567890abcdef"
            (root / ".env.example").write_text(
                secret_line + "\n",
                encoding="utf-8",
            )

            security = analyze_security(root)

        assert security.status == "attention needed"
        assert "<redacted>" in security.findings[0].evidence
        assert "<redacted>" in redact_secrets("token=" + "1234567890abcdef")


class TestPathSafety:
    def test_resolve_project_path_blocks_parent_escape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            with pytest.raises(ValueError):
                resolve_project_path(root, "../outside.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
