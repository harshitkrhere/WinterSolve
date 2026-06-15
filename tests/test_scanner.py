from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from wintersolve.modules.brain import build_brain_report
from wintersolve.modules.command_detector import detect_commands
from wintersolve.modules.debugger import analyze_error_text
from wintersolve.modules.docs_assistant import suggest_docs
from wintersolve.modules.explainer import explain_file
from wintersolve.modules.security import analyze_security, redact_secrets
from wintersolve.modules.scanner import scan_project
from wintersolve.project import resolve_project_path
from wintersolve.report import render_brain_report, render_scan_report


class ScannerTests(unittest.TestCase):
    def test_scan_detects_python_project_health_signals(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "demo.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_demo.py").write_text("def test_demo(): pass\n", encoding="utf-8")

            result = scan_project(root)

        self.assertTrue(result.exists)
        self.assertIn(("Python", 2), result.languages)
        self.assertIn("Python package", result.frameworks)
        self.assertIn("README.md", result.important_files)
        self.assertIn("tests", result.likely_test_paths)

    def test_scan_reports_missing_directory(self) -> None:
        result = scan_project(Path("definitely-missing-directory").resolve())

        self.assertFalse(result.exists)
        self.assertEqual(result.total_files, 0)
        self.assertTrue(result.risks)

    def test_markdown_report_renders_recommendations(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            result = scan_project(root)

        report = render_scan_report(result, output_format="markdown")

        self.assertIn("# WinterSolve Repo Scan", report)
        self.assertIn("## Recommendations", report)

    def test_explain_file_detects_python_symbols(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "demo.py"
            target.write_text("import os\n\nclass Demo:\n    pass\n", encoding="utf-8")

            result = explain_file(target)

        self.assertEqual(result.language, "Python")
        self.assertIn("class Demo", result.symbols)
        self.assertIn("os", result.imports)

    def test_debugger_detects_missing_python_module(self) -> None:
        result = analyze_error_text("ModuleNotFoundError: No module named 'demo'")

        self.assertEqual(result.likely_language, "Python")
        self.assertIn("Python dependency or import path issue", result.likely_causes)
        self.assertNotIn("DNS, host, or network configuration issue", result.likely_causes)

    def test_docs_assistant_suggests_missing_sections(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            result = suggest_docs(root)

        self.assertIn("Installation", result.missing_sections)
        self.assertIn("# Demo", result.readme_draft)

    def test_brain_report_generates_json_shape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n\n## Usage\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "demo.py").write_text("print('hello')\n", encoding="utf-8")

            report = build_brain_report(root)
            rendered = render_brain_report(report, output_format="json")

        self.assertIn('"identity"', rendered)
        self.assertIn('"security"', rendered)
        self.assertIn('"commands"', rendered)

    def test_command_detector_reads_package_scripts(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                '{"scripts":{"dev":"vite","test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )

            commands = detect_commands(root)

        self.assertIn("npm run dev", [command.command for command in commands])
        self.assertIn("npm run test", [command.command for command in commands])

    def test_security_redacts_secret_like_values(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            secret_line = "API_" + "KEY=" + "1234567890abcdef"
            (root / ".env.example").write_text(
                secret_line + "\n",
                encoding="utf-8",
            )

            security = analyze_security(root)

        self.assertEqual(security.status, "attention needed")
        self.assertIn("<redacted>", security.findings[0].evidence)
        self.assertIn("<redacted>", redact_secrets("token=" + "1234567890abcdef"))

    def test_resolve_project_path_blocks_parent_escape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            with self.assertRaises(ValueError):
                resolve_project_path(root, "../outside.py")

    def test_brain_report_handles_empty_repo(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_brain_report(root)

        self.assertTrue(report.identity.exists)
        self.assertIn("No files were found in the project directory.", report.risks)

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

        self.assertIn("Python package", report.stack)
        self.assertIn("Node.js", report.stack)
        self.assertIn(("Python", 1), report.languages)
        self.assertIn(("TypeScript", 1), report.languages)


if __name__ == "__main__":
    unittest.main()
