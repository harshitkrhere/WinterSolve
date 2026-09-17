from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from wintersolve.modules.security import (
    CATEGORY_BANDIT,
    CATEGORY_CODE_PATTERN,
    CATEGORY_SECRET,
    analyze_security,
    looks_like_real_secret,
    redact_secrets,
    strip_strings_and_comments,
)

from .conftest import write

# Built from pieces so the repository's own scan never flags this file.
FAKE_AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
FAKE_GITHUB_TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


class TestSecretDetection:
    def test_known_token_formats_are_high_severity_and_redacted(self, tmp_path: Path) -> None:
        write(tmp_path / "settings.py", f'AWS_KEY = "{FAKE_AWS_KEY}"\n')

        summary = analyze_security(tmp_path, run_bandit=False)

        assert summary.status == "attention needed"
        (finding,) = summary.findings
        assert finding.category == CATEGORY_SECRET
        assert finding.kind == "AWS access key"
        assert finding.severity == "high"
        assert FAKE_AWS_KEY not in finding.evidence
        assert "<redacted-secret>" in finding.evidence

    def test_generic_assignment_is_medium_severity(self, tmp_path: Path) -> None:
        write(tmp_path / ".env", "DB_PASSWORD=" + "s3cr3tpassw0rd99\n")

        (finding,) = analyze_security(tmp_path, run_bandit=False).findings

        assert finding.kind == "Hardcoded secret-like value"
        assert finding.severity == "medium"
        assert finding.evidence == "DB_PASSWORD=<redacted>"

    def test_placeholders_and_code_references_are_not_secrets(self, tmp_path: Path) -> None:
        write(
            tmp_path / "config.py",
            "\n".join(
                [
                    'PASSWORD = "changeme-please"',
                    "api_key = self.config.api_key or os.getenv('API_KEY')",
                    'token = "${GITHUB_TOKEN}"',
                    'secret = "<your-secret-here>"',
                ]
            ),
        )

        assert analyze_security(tmp_path, run_bandit=False).findings == []

    def test_secrets_are_found_in_prose_and_config_too(self, tmp_path: Path) -> None:
        write(tmp_path / "NOTES.md", f"Old token: {FAKE_GITHUB_TOKEN}\n")

        (finding,) = analyze_security(tmp_path, run_bandit=False).findings

        assert finding.kind == "GitHub token"
        assert finding.path == "NOTES.md"


class TestCodePatterns:
    def test_real_calls_are_flagged_but_mentions_are_not(self, tmp_path: Path) -> None:
        write(
            tmp_path / "runner.py",
            "\n".join(
                [
                    "# never eval(cmd) here",
                    'HELP = "avoid eval() and exec()"',
                    "def run(cmd):",
                    "    return eval(cmd)",
                ]
            ),
        )

        findings = analyze_security(tmp_path, run_bandit=False).findings

        assert [(f.kind, f.line) for f in findings] == [("eval() call", 4)]
        assert findings[0].category == CATEGORY_CODE_PATTERN

    def test_prose_files_never_get_code_pattern_findings(self, tmp_path: Path) -> None:
        write(tmp_path / "README.md", "Never call eval() on user input.\n")

        assert analyze_security(tmp_path, run_bandit=False).findings == []

    def test_sql_built_from_request_data_is_flagged(self, tmp_path: Path) -> None:
        # Assembled in pieces so the repository's own scan stays clean.
        sql = " ".join(["SELECT", "*", "FROM", "users", "WHERE", "id", "="])
        write(tmp_path / "views.py", f'cursor.execute("{sql} " + request.args["id"])\n')

        (finding,) = analyze_security(tmp_path, run_bandit=False).findings

        assert finding.kind == "SQL built from request data"

    def test_shell_true_and_pickle_are_flagged(self, tmp_path: Path) -> None:
        write(
            tmp_path / "tasks.py",
            'subprocess.run("ls " + name, shell=True)\ndata = pickle.loads(blob)\n',
        )

        kinds = [f.kind for f in analyze_security(tmp_path, run_bandit=False).findings]

        assert kinds == ["Shell command with shell=True", "Unsafe deserialization"]


class TestSummaryShape:
    def test_clean_project_is_clear_with_bandit_skipped(self, node_project: Path) -> None:
        summary = analyze_security(node_project)

        assert summary.status == "clear"
        assert summary.findings == []
        assert summary.files_checked == 5
        assert "Bandit skipped: no Python files found." in summary.notes

    def test_no_bandit_flag_is_explained(self, python_project: Path) -> None:
        summary = analyze_security(python_project, run_bandit=False)

        assert "Bandit skipped by request (--no-bandit)." in summary.notes

    def test_findings_are_sorted_by_severity(self, tmp_path: Path) -> None:
        write(tmp_path / "a.py", "x = eval(y)\n")
        write(tmp_path / "b.py", f'KEY = "{FAKE_AWS_KEY}"\n')

        severities = [f.severity for f in analyze_security(tmp_path, run_bandit=False).findings]

        assert severities == ["high", "medium"]


@pytest.mark.skipif(importlib.util.find_spec("bandit") is None, reason="bandit not installed")
class TestBanditIntegration:
    def test_bandit_findings_are_relative_and_categorised(self, tmp_path: Path) -> None:
        write(tmp_path / "src" / "load.py", "import pickle\n\npickle.loads(b'')\n")
        write(tmp_path / ".venv" / "lib" / "vendored.py", "import pickle\n\npickle.loads(b'')\n")

        summary = analyze_security(tmp_path)

        bandit = [f for f in summary.findings if f.category == CATEGORY_BANDIT]
        assert bandit, summary.notes
        assert all(f.path == "src/load.py" for f in bandit)  # .venv was excluded
        assert any(note.startswith("Bandit ran") for note in summary.notes)


class TestHelpers:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("s3cr3tpassw0rd99", True),
            ("changeme-please", False),
            ("self.config.api_key", False),
            ("os.getenv('X')", False),
            ("justletters", False),
            ("<placeholder>", False),
        ],
    )
    def test_looks_like_real_secret(self, value: str, expected: bool) -> None:
        assert looks_like_real_secret(value) is expected

    def test_redact_secrets_handles_known_and_generic_forms(self) -> None:
        assert redact_secrets(f"key={FAKE_AWS_KEY}") == "key=<redacted-secret>"
        assert redact_secrets("token=" + "1234567890abcdef") == "token=<redacted>"

    def test_strip_strings_and_comments(self) -> None:
        assert strip_strings_and_comments('x = eval("1")  # eval(y)') == 'x = eval("")  '
        assert strip_strings_and_comments("// eval(y)") == ""
        assert strip_strings_and_comments('url = "http://x/#a"') == 'url = ""'
