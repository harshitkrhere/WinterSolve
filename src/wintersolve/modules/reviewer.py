"""Pre-review checklist for local Git changes.

Looks at *which* files changed (via ``git status``), not at diffs, and turns
that into risks worth mentioning and a checklist worth running before asking
someone else for a review.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT_SECONDS = 10

CODE_SUFFIXES = (
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
)
CONFIG_SUFFIXES = (".yml", ".yaml", ".toml", ".json", ".ini", ".cfg", ".env")
DOC_NAMES = {"readme.md", "contributing.md", "security.md", "changelog.md"}


@dataclass(frozen=True)
class ReviewResult:
    path: Path
    git_available: bool
    changed_files: list[str]
    risks: list[str]
    checklist: list[str]


def review_changes(path: Path) -> ReviewResult:
    """Summarise uncommitted changes in the repository at ``path``."""
    status = _git_status(path)
    if status is None:
        return ReviewResult(
            path=path,
            git_available=False,
            changed_files=[],
            risks=["This folder is not a Git repository or Git is not available."],
            checklist=["Initialize Git or run this command inside a Git repository."],
        )

    changed_files = _parse_changed_files(status)
    return ReviewResult(
        path=path,
        git_available=True,
        changed_files=changed_files,
        risks=_build_risks(changed_files),
        checklist=_build_checklist(changed_files),
    )


def _git_status(path: Path) -> str | None:
    """Return ``git status --short`` output, or None when Git cannot answer."""
    try:
        completed = subprocess.run(  # fixed argv, never a shell
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=path,
            check=False,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _parse_changed_files(status_output: str) -> list[str]:
    """Extract paths from porcelain short status, following renames to the new name."""
    files: list[str] = []
    for line in status_output.splitlines():
        if not line.strip():
            continue
        entry = line[3:].strip()
        if " -> " in entry:
            entry = entry.split(" -> ")[-1]
        files.append(entry.strip('"'))
    return files


def _build_risks(changed_files: list[str]) -> list[str]:
    if not changed_files:
        return ["No local changes were detected."]

    lowered = [file.lower() for file in changed_files]
    risks: list[str] = []
    if any(file.endswith(CODE_SUFFIXES) for file in lowered):
        risks.append("Code files changed: tests or manual verification should be included.")
    if any(file.endswith(CONFIG_SUFFIXES) for file in lowered):
        risks.append("Configuration files changed: check setup, build, and CI behavior.")
    if any(".github/workflows" in file for file in lowered):
        risks.append("CI workflows changed: confirm permissions and secrets are still minimal.")
    if any("test" in file for file in lowered):
        risks.append("Test files changed: confirm tests still cover the intended behavior.")
    if any(file in DOC_NAMES for file in lowered):
        risks.append(
            "Project documentation changed: verify commands and examples are still accurate."
        )
    if any(file.endswith((".lock", "-lock.json", "-lock.yaml")) for file in lowered):
        risks.append("Lockfiles changed: make sure the dependency update was intentional.")
    return risks or ["No obvious review risks were detected from file names alone."]


def _build_checklist(changed_files: list[str]) -> list[str]:
    lowered = [file.lower() for file in changed_files]
    checklist = [
        "Summarize the behavior change in plain language.",
        "Run the relevant tests or explain why they were not run.",
        "Check whether documentation needs an update.",
    ]
    if any(file.endswith(CODE_SUFFIXES) for file in lowered):
        checklist.append("Review error handling and edge cases in changed code.")
    if any(file.endswith(CONFIG_SUFFIXES) for file in lowered):
        checklist.append("Validate changed configuration files before merging.")
    if any(file.endswith((".env", ".pem", ".key")) or "secret" in file for file in lowered):
        checklist.append("Double-check that no credentials are being committed.")
    return checklist
