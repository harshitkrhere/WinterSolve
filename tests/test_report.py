from __future__ import annotations

import json
from pathlib import Path

from wintersolve.modules.debugger import analyze_error_text
from wintersolve.modules.docs_assistant import suggest_docs
from wintersolve.modules.explainer import explain_file
from wintersolve.modules.scanner import scan_project
from wintersolve.report import (
    render_debug_analysis,
    render_docs_suggestions,
    render_explanation,
    render_scan_report,
)

from .conftest import write


class TestScanRenderers:
    def test_text_lists_sections_and_none_detected(self, empty_project: Path) -> None:
        text = render_scan_report(scan_project(empty_project))

        assert text.startswith("WinterSolve Repo Scan\n=====================\n")
        assert "Languages:\n  - None detected" in text
        assert "Risks:\n  - No files were found in the project directory." in text

    def test_markdown_uses_headings_and_bullets(self, python_project: Path) -> None:
        markdown = render_scan_report(scan_project(python_project), output_format="markdown")

        assert markdown.startswith("# WinterSolve Repo Scan\n")
        assert "## Detected Stack\n\n- Python package" in markdown
        assert "## Recommendations" in markdown

    def test_json_is_parseable_and_sorted(self, python_project: Path) -> None:
        payload = json.loads(render_scan_report(scan_project(python_project), output_format="json"))

        assert payload["exists"] is True
        assert list(payload) == sorted(payload)


class TestOtherRenderers:
    def test_explanation_includes_parse_errors_section(self, tmp_path: Path) -> None:
        text = render_explanation(explain_file(write(tmp_path / "bad.py", "def (:\n")))

        assert "Parse errors:\n  - Python syntax error near line 1" in text

    def test_explanation_hides_error_section_when_clean(self, tmp_path: Path) -> None:
        text = render_explanation(explain_file(write(tmp_path / "ok.py", "x = 1\n")))

        assert "Parse errors" not in text

    def test_debug_and_docs_titles(self, python_project: Path) -> None:
        assert render_debug_analysis(analyze_error_text("KeyError: 'x'")).startswith(
            "WinterSolve Debug Analysis"
        )
        docs = render_docs_suggestions(suggest_docs(python_project), include_draft=True)
        assert "README Draft:" in docs
        assert "# Demo" in docs
