from __future__ import annotations

from pathlib import Path

import pytest

from wintersolve.modules.debugger import analyze_error_file, analyze_error_text

from .conftest import write

PYTHON_TRACE = """Traceback (most recent call last):
  File "app/main.py", line 12, in <module>
    import demo
ModuleNotFoundError: No module named 'demo'
"""

NODE_TRACE = """Error: Cannot find module 'left-pad'
    at Function.Module._resolveFilename (node:internal/modules/cjs/loader:1077:15)
    at Object.<anonymous> (/srv/app/src/index.js:3:15)
"""


class TestAnalyzeErrorText:
    def test_python_missing_module(self) -> None:
        result = analyze_error_text(PYTHON_TRACE)

        assert result.likely_language == "Python"
        assert result.likely_causes == ["Python dependency or import path issue"]
        assert result.signals == ["Python stack frame: app/main.py:12"]
        assert (
            "Start with the first stack frame that points into your project code."
            in result.next_steps
        )

    def test_node_missing_module_with_js_frames(self) -> None:
        result = analyze_error_text(NODE_TRACE)

        assert result.likely_language == "Node.js"
        assert "Node.js dependency or path issue" in result.likely_causes
        assert "JavaScript stack frame: /srv/app/src/index.js:3:15" in result.signals

    @pytest.mark.parametrize(
        ("text", "cause"),
        [
            (
                "EADDRINUSE: address already in use :::3000",
                "Port is already in use by another process",
            ),
            (
                "requests.exceptions.SSLError: CERTIFICATE_VERIFY_FAILED",
                "TLS certificate or SSL configuration issue",
            ),
            ("npm ERR! ERESOLVE unable to resolve dependency tree", "Dependency version conflict"),
            (
                "AttributeError: 'NoneType' object has no attribute 'x'",
                "Attribute or method does not exist on that object (often None)",
            ),
        ],
    )
    def test_common_signatures(self, text: str, cause: str) -> None:
        assert cause in analyze_error_text(text).likely_causes

    def test_unknown_error_is_honest(self) -> None:
        result = analyze_error_text("something odd happened")

        assert result.likely_language == "Unknown"
        assert result.likely_causes == [
            "No known error pattern matched. More context may be needed."
        ]
        assert result.signals == ["No stack-frame signals were detected."]


class TestAnalyzeErrorFile:
    def test_reads_log_file(self, tmp_path: Path) -> None:
        log = write(tmp_path / "error.log", PYTHON_TRACE)

        result = analyze_error_file(log)

        assert result.source == str(log)
        assert result.likely_language == "Python"

    def test_missing_file(self, tmp_path: Path) -> None:
        result = analyze_error_file(tmp_path / "missing.log")

        assert result.likely_causes == [f"Error file does not exist: {tmp_path / 'missing.log'}"]
