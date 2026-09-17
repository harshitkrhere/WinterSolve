"""Repo Brain: compose every analyzer into one project intelligence report."""

from __future__ import annotations

from pathlib import Path

from wintersolve.models import BrainReport, ProjectIdentity, SecuritySummary
from wintersolve.modules.architecture import map_architecture
from wintersolve.modules.command_detector import detect_commands
from wintersolve.modules.docs_assistant import suggest_docs
from wintersolve.modules.recommendations import (
    build_brain_recommendations,
    build_brain_risks,
    build_docs_health,
    build_next_actions,
)
from wintersolve.modules.scanner import scan_project
from wintersolve.modules.security import analyze_security


def build_brain_report(root: Path, *, run_bandit: bool = True) -> BrainReport:
    """Analyze ``root`` with every module and assemble the combined report.

    ``run_bandit=False`` skips the optional Bandit pass, which is the slow part
    on large Python projects.
    """
    scan = scan_project(root)
    if not scan.exists:
        return _missing_project_report(root, scan.risks, scan.recommendations)

    docs = suggest_docs(root, scan)
    commands = detect_commands(root)
    security = analyze_security(root, run_bandit=run_bandit)
    architecture = map_architecture(root)
    risks = build_brain_risks(scan, security, len(commands))

    return BrainReport(
        identity=ProjectIdentity(name=root.name, path=str(root), exists=True, offline_mode=True),
        languages=scan.languages,
        stack=scan.frameworks,
        source_paths=scan.likely_source_paths,
        test_paths=scan.likely_test_paths,
        docs_health=build_docs_health(docs.missing_sections, scan.missing_recommended_files),
        architecture=architecture,
        commands=commands,
        security=security,
        risks=risks,
        recommendations=build_brain_recommendations(scan, security, len(commands)),
        next_actions=build_next_actions(
            security=security,
            command_count=len(commands),
            has_architecture=bool(architecture),
            risk_count=len(risks),
        ),
    )


def _missing_project_report(
    root: Path, risks: list[str], recommendations: list[str]
) -> BrainReport:
    return BrainReport(
        identity=ProjectIdentity(name=root.name, path=str(root), exists=False, offline_mode=True),
        languages=[],
        stack=[],
        source_paths=[],
        test_paths=[],
        docs_health=["Project path does not exist, so documentation health could not be checked."],
        architecture=[],
        commands=[],
        security=SecuritySummary.empty(),
        risks=risks,
        recommendations=recommendations,
        next_actions=["Point WinterSolve at an existing project directory."],
    )
