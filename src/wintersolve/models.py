"""Result types shared by the Repo Brain report and the analyzers that feed it.

Every result is a frozen dataclass so it can be rendered as text, Markdown, or
JSON without surprises. Analyzers build these; they never print.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

# Bump when the shape of the JSON report changes in a way integrations must
# know about. Additive fields do not require a bump.
BRAIN_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectIdentity:
    name: str
    path: str
    exists: bool
    offline_mode: bool


@dataclass(frozen=True)
class CommandCandidate:
    """A setup, build, test, or run command inferred from project files."""

    name: str
    command: str
    source: str
    confidence: str


@dataclass(frozen=True)
class ArchitectureSection:
    """A top-level area of the repository and what it is probably for."""

    name: str
    path: str
    purpose: str
    notable_files: list[str]


@dataclass(frozen=True)
class SecurityFinding:
    """One thing the security scan wants a human to look at.

    ``category`` is one of ``secret``, ``code-pattern``, or ``bandit`` and is
    the field integrations should branch on; ``kind`` is the human label.
    """

    path: str
    line: int
    category: str
    kind: str
    severity: str
    evidence: str


@dataclass(frozen=True)
class SecuritySummary:
    status: str
    offline_by_default: bool
    files_checked: int
    findings: list[SecurityFinding]
    notes: list[str]

    @staticmethod
    def empty() -> SecuritySummary:
        return SecuritySummary(
            status="not checked",
            offline_by_default=True,
            files_checked=0,
            findings=[],
            notes=["Project path does not exist."],
        )


@dataclass(frozen=True)
class BrainReport:
    """The full Repo Brain result: everything WinterSolve learned about a project."""

    identity: ProjectIdentity
    languages: list[tuple[str, int]]
    stack: list[str]
    source_paths: list[str]
    test_paths: list[str]
    docs_health: list[str]
    architecture: list[ArchitectureSection]
    commands: list[CommandCandidate]
    security: SecuritySummary
    risks: list[str]
    recommendations: list[str]
    next_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain JSON-friendly data with a stable, documented shape."""
        data = asdict(self)
        data["schema_version"] = BRAIN_SCHEMA_VERSION
        data["languages"] = [{"name": name, "files": count} for name, count in self.languages]
        for finding in data["security"]["findings"]:
            finding["evidence"] = strip_control_characters(finding["evidence"])
        return data


def strip_control_characters(text: str) -> str:
    """Remove control characters so evidence snippets stay clean in JSON and terminals."""
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", text)
