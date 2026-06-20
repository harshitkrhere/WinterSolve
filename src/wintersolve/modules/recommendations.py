from __future__ import annotations

from wintersolve.models import SecuritySummary
from wintersolve.modules.scanner import RECOMMEND_DOCUMENT_COMMANDS, ScanResult


def build_docs_health(
    missing_sections: list[str], missing_files: list[str]
) -> list[str]:
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


def build_brain_risks(
    scan: ScanResult, security: SecuritySummary, command_count: int
) -> list[str]:
    risks = list(scan.risks)
    if security.findings:
        secrets = sum(
            1
            for f in security.findings
            if "secret" in f.kind.lower()
            or "token" in f.kind.lower()
            or "key" in f.kind.lower()
        )
        vulns = len(security.findings) - secrets
        if secrets > 0:
            risks.append(f"{secrets} potential secret exposure(s) detected.")
        if vulns > 0:
            risks.append(
                f"{vulns} potential code vulnerabilities detected in the audit."
            )
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
    if security.findings:
        kinds = {f.kind.lower() for f in security.findings}
        if any("secret" in k or "token" in k or "key" in k for k in kinds):
            recommendations.append(
                "Rotate exposed credentials found in the security audit."
            )
        if any("sql" in k for k in kinds):
            framework_hint = "using an ORM or parameterized queries"
            if scan.frameworks:
                framework_hint = f"using an ORM suitable for {scan.frameworks[0]}"
            recommendations.append(f"Mitigate SQL Injection risks by {framework_hint}.")
        if any("eval" in k or "exec" in k or "shell" in k for k in kinds):
            recommendations.append(
                "Refactor unsafe eval/exec or shell invocations to use "
                "safer alternatives (e.g. ast.literal_eval)."
            )
        if any("deserialization" in k or "pickle" in k for k in kinds):
            recommendations.append(
                "Replace unsafe deserialization (like pickle) with safe formats "
                "like JSON."
            )
        if any("bandit" in k for k in kinds):
            recommendations.append(
                "Review and fix the specific static analysis issues flagged by Bandit."
            )
    if command_count == 0:
        recommendations.append(
            "Document setup, run, build, and test commands in README.md."
        )
    if scan.likely_source_paths and scan.likely_test_paths:
        recommendations.append(
            "Connect source areas to test coverage in contributor documentation."
        )
    return _dedupe(recommendations)


def build_next_actions(
    security: SecuritySummary,
    command_count: int,
    has_architecture: bool,
) -> list[str]:
    actions = [
        "Start with the highest-risk item in the Risks section.",
        "Run or document the detected test command before major changes.",
        "Use `wintersolve explain <file>` on the most important source files.",
    ]
    if security.findings:
        high_sev = sum(1 for f in security.findings if f.severity == "high")
        if high_sev > 0:
            actions.insert(
                0,
                f"Fix the {high_sev} high-severity security vulnerabilities "
                "immediately.",
            )
        else:
            actions.insert(
                0,
                "Review the potential security findings before sharing this "
                "repository or report.",
            )
    if command_count == 0:
        actions.insert(
            0,
            "Add documented setup and test commands so contributors can be productive.",
        )
    if has_architecture:
        actions.append(
            "Use the architecture map as the first contributor onboarding guide."
        )
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
