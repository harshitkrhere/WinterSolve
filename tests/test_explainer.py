from __future__ import annotations

from pathlib import Path

from wintersolve.modules.explainer import explain_file
from wintersolve.project import MAX_TEXT_FILE_BYTES

from .conftest import write


class TestPythonFiles:
    def test_detects_symbols_imports_and_docstring(self, tmp_path: Path) -> None:
        target = write(
            tmp_path / "demo.py",
            '"""Demo module.\n\nMore detail.\n"""\n\nimport os\nfrom pathlib import Path\n\n\n'
            "class Demo:\n    pass\n\n\ndef helper():\n    pass\n\n\n"
            'if __name__ == "__main__":\n    helper()\n',
        )

        result = explain_file(target)

        assert result.language == "Python"
        assert result.symbols == [
            "class Demo",
            "function helper",
            "runnable as a script (__main__ guard)",
        ]
        assert result.imports == ["os", "pathlib"]
        assert "Its docstring says: Demo module." in result.summary
        assert result.errors == []

    def test_syntax_errors_are_surfaced_not_swallowed(self, tmp_path: Path) -> None:
        target = write(tmp_path / "broken.py", "def broken(:\n    pass\n")

        result = explain_file(target)

        assert result.errors and result.errors[0].startswith("Python syntax error near line 1")
        assert "The file does not parse; fix the reported syntax error first." in result.risks


class TestOtherFiles:
    def test_generic_analysis_for_javascript(self, tmp_path: Path) -> None:
        source = "\n".join(
            [
                "import x from 'x'",
                "const y = require('y')",
                "",
                "export function main() {}",
                "class App {}",
            ]
        )
        target = write(tmp_path / "app.js", source + "\n")

        result = explain_file(target)

        assert result.language == "JavaScript"
        assert "export function main() {}" in result.symbols
        assert "class App {}" in result.symbols
        assert result.imports == ["import x from 'x'"]

    def test_data_formats_get_a_label(self, tmp_path: Path) -> None:
        assert explain_file(write(tmp_path / "config.toml", "a = 1\n")).language == "TOML"
        assert explain_file(write(tmp_path / "notes.txt", "hello\n")).language == "Text"

    def test_unknown_extensions_are_not_analyzed(self, tmp_path: Path) -> None:
        result = explain_file(write(tmp_path / "notes", "hello\n"))

        assert result.language == "Binary or large file"
        assert result.risks == ["File is too large or not recognized as text."]

    def test_large_file_is_skipped(self, tmp_path: Path) -> None:
        target = write(tmp_path / "bundle.js", "x" * (MAX_TEXT_FILE_BYTES + 1))

        result = explain_file(target)

        assert result.language == "Binary or large file"
        assert result.line_count == 0

    def test_missing_file(self, tmp_path: Path) -> None:
        result = explain_file(tmp_path / "nope.py")

        assert not result.exists
        assert result.risks == [f"File does not exist: {tmp_path / 'nope.py'}"]

    def test_long_file_without_structure_is_a_risk(self, tmp_path: Path) -> None:
        target = write(tmp_path / "dump.txt", "line\n" * 200)

        assert (
            "Long file with no obvious symbols or sections detected." in explain_file(target).risks
        )
