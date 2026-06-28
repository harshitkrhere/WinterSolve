from __future__ import annotations

from pathlib import Path

from wintersolve.models import (
    BrainReport,
    ProjectIdentity,
    SecuritySummary,
    path_to_display,
)
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


def build_brain_report(root: Path) -> BrainReport:
    scan = scan_project(root)
    docs = suggest_docs(root, scan) if scan.exists else None
    commands = detect_commands(root) if scan.exists else []
    security = analyze_security(root) if scan.exists else SecuritySummary.empty()
    architecture = map_architecture(root) if scan.exists else []

    identity = ProjectIdentity(
        name=root.name,
        path=path_to_display(root),
        exists=scan.exists,
        offline_mode=True,
    )
    docs_health = (
        build_docs_health(docs.missing_sections, scan.missing_recommended_files)
        if docs
        else ["Project path does not exist, so documentation health could not be checked."]
    )
    risks = build_brain_risks(scan, security, len(commands))
    recommendations = build_brain_recommendations(scan, security, len(commands))

    next_actions = build_next_actions(
        security=security,
        command_count=len(commands),
        has_architecture=bool(architecture),
    )

    return BrainReport(
        identity=identity,
        languages=scan.languages,
        stack=scan.frameworks,
        source_paths=scan.likely_source_paths,
        test_paths=scan.likely_test_paths,
        docs_health=docs_health,
        architecture=architecture,
        commands=commands,
        security=security,
        risks=risks,
        recommendations=recommendations,
        next_actions=next_actions,
    )
