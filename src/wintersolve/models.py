from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectIdentity:
    name: str
    path: str
    exists: bool
    offline_mode: bool


@dataclass(frozen=True)
class CommandCandidate:
    name: str
    command: str
    source: str
    confidence: str


@dataclass(frozen=True)
class ArchitectureSection:
    name: str
    path: str
    purpose: str
    notable_files: list[str]


@dataclass(frozen=True)
class SecurityFinding:
    path: str
    line: int
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
        data = asdict(self)
        data["languages"] = [
            {"name": name, "files": count} for name, count in self.languages
        ]
        return data


def path_to_display(path: Path) -> str:
    return str(path)
