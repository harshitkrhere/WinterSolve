from __future__ import annotations

import json
from pathlib import Path

from wintersolve.models import BRAIN_SCHEMA_VERSION, SecurityFinding, SecuritySummary
from wintersolve.modules.brain import build_brain_report
from wintersolve.modules.recommendations import (
    build_brain_recommendations,
    build_brain_risks,
    build_next_actions,
)
from wintersolve.modules.scanner import scan_project
from wintersolve.report import render_brain_report

from .conftest import write


def finding(category: str, kind: str, severity: str = "medium") -> SecurityFinding:
    return SecurityFinding(
        path="x.py", line=1, category=category, kind=kind, severity=severity, evidence="..."
    )


def summary(*findings: SecurityFinding) -> SecuritySummary:
    return SecuritySummary(
        status="attention needed" if findings else "clear",
        offline_by_default=True,
        files_checked=1,
        findings=list(findings),
        notes=[],
    )


class TestBuildBrainReport:
    def test_json_shape_is_stable(self, python_project: Path) -> None:
        report = build_brain_report(python_project, run_bandit=False)
        data = json.loads(render_brain_report(report, output_format="json"))

        assert data["schema_version"] == BRAIN_SCHEMA_VERSION
        assert data["identity"]["name"] == python_project.name
        assert {"name": "Python", "files": 3} in data["languages"]
        assert data["commands"][0]["command"] == "python -m pip install -e ."
        assert data["security"]["status"] == "clear"
        assert set(data) >= {"architecture", "risks", "recommendations", "next_actions"}

    def test_handles_empty_repo(self, empty_project: Path) -> None:
        report = build_brain_report(empty_project, run_bandit=False)

        assert report.identity.exists
        assert "No files were found in the project directory." in report.risks

    def test_handles_missing_repo(self, tmp_path: Path) -> None:
        report = build_brain_report(tmp_path / "missing", run_bandit=False)

        assert not report.identity.exists
        assert report.security.status == "not checked"
        assert report.next_actions == ["Point WinterSolve at an existing project directory."]

    def test_detects_mixed_python_node_repo(self, tmp_path: Path) -> None:
        write(tmp_path / "README.md", "# Mixed\n")
        write(tmp_path / "pyproject.toml", "[project]\nname = 'mixed'\n")
        write(tmp_path / "package.json", '{"scripts": {"test": "vitest"}}')
        write(tmp_path / "src" / "app.py", "print('hi')\n")
        write(tmp_path / "src" / "app.ts", "console.log('hi')\n")

        report = build_brain_report(tmp_path, run_bandit=False)

        assert report.stack == ["Node.js", "Python package"]
        assert ("Python", 1) in report.languages
        assert ("TypeScript", 1) in report.languages

    def test_clean_project_reads_calmly(self, python_project: Path) -> None:
        for name in ("CONTRIBUTING.md", "SECURITY.md"):
            write(python_project / name, "x\n")

        report = build_brain_report(python_project, run_bandit=False)

        assert report.risks == []
        assert report.recommendations == [
            "Nothing urgent. Keep docs, tests, and project metadata current as the project grows."
        ]
        assert "Start with the highest-risk item in the Risks section." not in report.next_actions


class TestRecommendationRules:
    def test_secret_findings_drive_risks_recommendations_and_actions(
        self, python_project: Path
    ) -> None:
        scan = scan_project(python_project)
        security = summary(finding("secret", "AWS access key", "high"))

        risks = build_brain_risks(scan, security, command_count=2)
        recommendations = build_brain_recommendations(scan, security, command_count=2)
        actions = build_next_actions(security, command_count=2, has_architecture=True, risk_count=1)

        assert "1 possible hardcoded secret(s) found." in risks
        assert any(r.startswith("Move secrets to environment variables") for r in recommendations)
        assert actions[0] == "Review the 1 high-severity security finding(s) first."

    def test_code_pattern_advice_is_specific(self, python_project: Path) -> None:
        scan = scan_project(python_project)
        security = summary(
            finding("code-pattern", "eval() call"),
            finding("code-pattern", "Shell command with shell=True"),
        )

        recommendations = build_brain_recommendations(scan, security, command_count=2)

        assert (
            "Replace eval() with a safe parser such as ast.literal_eval or json.loads."
            in recommendations
        )
        assert any("shell=True" in r for r in recommendations)

    def test_no_commands_is_called_out(self, empty_project: Path) -> None:
        scan = scan_project(empty_project)

        risks = build_brain_risks(scan, summary(), command_count=0)
        actions = build_next_actions(summary(), command_count=0, has_architecture=False)

        assert "No setup, test, build, or run commands were detected." in risks
        assert actions[0].startswith("Add documented setup and test commands")
