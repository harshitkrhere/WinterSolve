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
        assert result.signals == [
            "Message: ModuleNotFoundError: No module named 'demo'",
            "Python stack frame: app/main.py:12",
        ]
        assert result.next_steps[:2] == [
            "Start at app/main.py, line 12: the deepest stack frame in your own code.",
            "If `demo` is a third-party package, install it: `python -m pip install demo`.",
        ]

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


class TestNextSteps:
    """Advice belongs to the rule that matched, and names what the error names."""

    def test_import_errors_never_get_unrelated_advice(self) -> None:
        # "import" contains "port" and "path"; neither may leak port or PATH advice in.
        steps = " ".join(analyze_error_text(PYTHON_TRACE).next_steps)

        assert "port" not in steps.replace("import", "")
        assert "PATH" not in steps

    @pytest.mark.parametrize(
        ("module", "install"),
        [
            ("cv2", "python -m pip install opencv-python"),
            ("yaml", "python -m pip install PyYAML"),
            ("requests", "python -m pip install requests"),
            ("distutils", "python -m pip install setuptools"),
        ],
    )
    def test_missing_python_module_names_the_package(self, module: str, install: str) -> None:
        steps = analyze_error_text(f"ModuleNotFoundError: No module named '{module}'").next_steps

        assert any(install in step for step in steps)

    def test_submodule_of_an_installed_package_is_a_version_question(self) -> None:
        text = "ModuleNotFoundError: No module named 'google.cloud.storage'"

        steps = analyze_error_text(text).next_steps

        assert any("python -m pip show google" in step for step in steps)
        assert not any("pip install google" in step for step in steps)

    def test_a_local_file_shadowing_a_package_is_called_out(self) -> None:
        text = "ModuleNotFoundError: No module named 'random.x'; 'random' is not a package"

        (first, *_) = analyze_error_text(text).next_steps

        assert "named `random` in your project is probably hiding" in first

    @pytest.mark.parametrize(
        ("specifier", "expected"),
        [
            ("express", "npm install express"),
            ("lodash/fp", "npm install lodash"),
            ("@scope/pkg/sub", "npm install @scope/pkg"),
            ("./routes/users", "`./routes/users` is a file path, not a package"),
        ],
    )
    def test_missing_node_module(self, specifier: str, expected: str) -> None:
        steps = analyze_error_text(f"Error: Cannot find module '{specifier}'").next_steps

        assert any(expected in step for step in steps)

    @pytest.mark.parametrize(
        "text",
        [
            "Error: listen EADDRINUSE: address already in use :::3000",
            "OSError: address already in use 127.0.0.1:3000",
        ],
    )
    def test_busy_port_is_named(self, text: str) -> None:
        steps = analyze_error_text(text).next_steps

        assert steps[0].startswith("Find what is using port 3000: `lsof -i :3000`")

    @pytest.mark.parametrize(
        "text",
        [
            "bash: pytest: command not found",
            "zsh: command not found: pytest",
            "'pytest' is not recognized as an internal or external command,",
        ],
    )
    def test_missing_command_is_named(self, text: str) -> None:
        steps = analyze_error_text(text).next_steps

        assert steps[0].startswith("`pytest` is not installed or not on PATH")

    def test_javascript_undefined_property(self) -> None:
        text = (
            "TypeError: Cannot read properties of undefined (reading 'map')\n"
            "    at App (src/App.jsx:12:20)\n"
            "    at renderWithHooks (node_modules/react-dom/cjs/react-dom.js:16305:18)\n"
        )

        result = analyze_error_text(text)

        assert result.likely_language == "JavaScript"
        assert result.likely_causes[0] == (
            "A value was undefined or null when the code read a property from it"
        )
        assert result.next_steps[0] == (
            "Start at src/App.jsx, line 12: the deepest stack frame in your own code."
        )

    def test_python_frames_inside_libraries_are_skipped(self) -> None:
        text = (
            "Traceback (most recent call last):\n"
            '  File "/srv/app/main.py", line 9, in <module>\n'
            '  File "/srv/.venv/lib/python3.12/site-packages/requests/api.py", line 73, in get\n'
            "requests.exceptions.ConnectionError: connection refused\n"
        )

        steps = analyze_error_text(text).next_steps

        assert (
            steps[0]
            == "Start at /srv/app/main.py, line 9: the deepest stack frame in your own code."
        )

    def test_line_numbers_are_not_mistaken_for_http_status_codes(self) -> None:
        text = "File \"views.py\", line 403, in handler\nKeyError: 'user'\n"

        assert analyze_error_text(text).likely_causes == [
            "Missing dictionary key or configuration value"
        ]

    def test_unmatched_errors_ask_for_more_output(self) -> None:
        steps = analyze_error_text("something odd happened").next_steps

        assert steps[0].startswith("Re-run the failing command and capture the full error output")
