"""Turn analyzer results into risks, recommendations, and next actions.

This is where the Repo Brain report gets its opinions. Rules here should be
specific enough to be actionable and humble enough to be true: analyzers
produce leads, and the wording should say so.
"""

from __future__ import annotations

from collections import Counter

from wintersolve.models import SecurityFinding, SecuritySummary
from wintersolve.modules.scanner import RECOMMEND_DOCUMENT_COMMANDS, ScanResult
from wintersolve.modules.security import (
    CATEGORY_BANDIT,
    CATEGORY_CODE_PATTERN,
    CATEGORY_SECRET,
)

# Advice keyed by the exact ``kind`` labels the security module produces.
ADVICE_BY_CODE_PATTERN = {
    "SQL built from request data": (
        "Use parameterized queries or an ORM instead of building SQL from request data."
    ),
    "eval() call": "Replace eval() with a safe parser such as ast.literal_eval or json.loads.",
    "exec() call": "Replace exec() with explicit imports or a plugin registry.",
    "Shell command with shell=True": (
        "Pass commands as argument lists without shell=True so input cannot inject commands."
    ),
    "Unsafe deserialization": (
        "Replace pickle/marshal/yaml.load with JSON or yaml.safe_load for untrusted data."
    ),
}


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
    counts = _count_by_category(security.findings)

    if counts[CATEGORY_SECRET]:
        risks.append(f"{counts[CATEGORY_SECRET]} possible hardcoded secret(s) found.")
    if counts[CATEGORY_CODE_PATTERN]:
        risks.append(
            f"{counts[CATEGORY_CODE_PATTERN]} risky code pattern(s) found "
            "(eval/exec, shell=True, unsafe deserialization, or SQL string building)."
        )
    if counts[CATEGORY_BANDIT]:
        risks.append(f"Bandit reported {counts[CATEGORY_BANDIT]} medium or high severity issue(s).")
    if command_count == 0:
        risks.append("No setup, test, build, or run commands were detected.")
    if not scan.likely_source_paths:
        risks.append("No clear source directory was detected.")
    return _dedupe(risks)


def build_brain_recommendations(
    scan: ScanResult, security: SecuritySummary, command_count: int
) -> list[str]:
    recommendations = [
        recommendation
        for recommendation in scan.recommendations
        if not (command_count > 0 and recommendation == RECOMMEND_DOCUMENT_COMMANDS)
    ]

    categories = {finding.category for finding in security.findings}
    if CATEGORY_SECRET in categories:
        recommendations.append(
            "Move secrets to environment variables or a secrets manager, "
            "then rotate any credential that was real."
        )
    for kind in sorted({f.kind for f in security.findings if f.category == CATEGORY_CODE_PATTERN}):
        advice = ADVICE_BY_CODE_PATTERN.get(kind)
        if advice:
            recommendations.append(advice)
    if CATEGORY_BANDIT in categories:
        recommendations.append(
            "Review the Bandit findings and fix or explicitly suppress each one."
        )

    if command_count == 0:
        recommendations.append("Document setup, run, build, and test commands in README.md.")
    return _dedupe(recommendations) or [
        "Nothing urgent. Keep docs, tests, and project metadata current as the project grows."
    ]


def build_next_actions(
    security: SecuritySummary,
    command_count: int,
    has_architecture: bool,
    risk_count: int = 0,
) -> list[str]:
    actions: list[str] = []

    high_severity = sum(1 for finding in security.findings if finding.severity == "high")
    if high_severity:
        actions.append(f"Review the {high_severity} high-severity security finding(s) first.")
    elif security.findings:
        actions.append("Review the security findings before sharing this repository or report.")

    if command_count == 0:
        actions.append("Add documented setup and test commands so contributors can be productive.")
    else:
        actions.append("Run the detected test command before making changes.")

    if risk_count:
        actions.append("Start with the highest-risk item in the Risks section.")
    actions.append("Use `wintersolve explain <file>` on the most important source files.")
    if has_architecture:
        actions.append("Use the architecture map as the first contributor onboarding guide.")
    return _dedupe(actions)


def _count_by_category(findings: list[SecurityFinding]) -> Counter[str]:
    return Counter(finding.category for finding in findings)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique
