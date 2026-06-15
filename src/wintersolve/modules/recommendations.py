from __future__ import annotations

from wintersolve.models import BrainReport, SecuritySummary
from wintersolve.modules.scanner import ScanResult


def build_docs_health(missing_sections: list[str], missing_files: list[str]) -> list[str]:
    health: list[str] = []
    if missing_sections:
        health.append(f"README is missing sections: {', '.join(missing_sections[:6])}.")
    else:
        health.append("README contains the expected core sections.")
    if missing_files:
        health.append(f"Missing project hygiene files: {', '.join(missing_files)}.")
    else:
        health.append("Core open-source hygiene files are present.")
    return health


def build_brain_risks(scan: ScanResult, security: SecuritySummary, command_count: int) -> list[str]:
    risks = list(scan.risks)
    if security.findings:
        risks.append(f"{len(security.findings)} potential secret exposure(s) detected.")
    if command_count == 0:
        risks.append("No setup, test, build, or run commands were detected.")
    if not scan.likely_source_paths:
        risks.append("No clear source directory was detected.")
    return _dedupe(risks)


def build_brain_recommendations(scan: ScanResult, security: SecuritySummary, command_count: int) -> list[str]:
    recommendations = [
        recommendation
        for recommendation in scan.recommendations
        if not (
            command_count > 0
            and recommendation.startswith("Document the main setup, test, and build commands")
        )
    ]
    if security.findings:
        recommendations.append("Review security findings and rotate any exposed credentials.")
    if command_count == 0:
        recommendations.append("Document setup, run, build, and test commands in README.md.")
    if scan.likely_source_paths and scan.likely_test_paths:
        recommendations.append("Connect source areas to test coverage in contributor documentation.")
    return _dedupe(recommendations)


def build_next_actions(report: BrainReport) -> list[str]:
    actions = [
        "Start with the highest-risk item in the Risks section.",
        "Run or document the detected test command before major changes.",
        "Use `wintersolve explain <file>` on the most important source files.",
    ]
    if report.security.findings:
        actions.insert(0, "Review potential secrets before sharing this repository or report.")
    if not report.commands:
        actions.insert(0, "Add documented setup and test commands so contributors can be productive.")
    if report.architecture:
        actions.append("Use the architecture map as the first contributor onboarding guide.")
    return _dedupe(actions)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique
