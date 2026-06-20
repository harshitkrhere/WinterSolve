from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewResult:
    path: Path
    git_available: bool
    changed_files: list[str]
    risks: list[str]
    checklist: list[str]


def review_changes(path: Path) -> ReviewResult:
    status = _run_git(path, ["status", "--short"])
    if status is None:
        return ReviewResult(
            path=path,
            git_available=False,
            changed_files=[],
            risks=["This folder is not a Git repository or Git is not available."],
            checklist=["Initialize Git or run this command inside a Git repository."],
        )

    changed_files = _parse_changed_files(status)
    risks = _build_risks(changed_files)
    checklist = _build_checklist(changed_files)
    return ReviewResult(
        path=path,
        git_available=True,
        changed_files=changed_files,
        risks=risks,
        checklist=checklist,
    )


def _run_git(path: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=path,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _parse_changed_files(status_output: str) -> list[str]:
    files: list[str] = []
    for line in status_output.splitlines():
        if not line.strip():
            continue
        entry = line[3:].strip()
        if " -> " in entry:
            entry = entry.split(" -> ")[-1]
        files.append(entry)
    return files


def _build_risks(changed_files: list[str]) -> list[str]:
    if not changed_files:
        return ["No local changes were detected."]

    risks: list[str] = []
    if any(
        file.endswith((".py", ".js", ".ts", ".tsx", ".go", ".rs"))
        for file in changed_files
    ):
        risks.append(
            "Code files changed: tests or manual verification should be included."
        )
    if any(
        file.endswith((".yml", ".yaml", ".toml", ".json")) for file in changed_files
    ):
        risks.append(
            "Configuration files changed: check setup, build, and CI behavior."
        )
    if any("test" in file.lower() for file in changed_files):
        risks.append(
            "Test files changed: confirm tests still cover the intended behavior."
        )
    if any(
        file.lower() in {"readme.md", "contributing.md", "security.md"}
        for file in changed_files
    ):
        risks.append(
            "Project documentation changed: verify commands and examples are "
            "still accurate."
        )
    return risks or ["No obvious review risks were detected from file names alone."]


def _build_checklist(changed_files: list[str]) -> list[str]:
    checklist = [
        "Summarize the behavior change in plain language.",
        "Run the relevant tests or explain why they were not run.",
        "Check whether documentation needs an update.",
    ]
    if any(file.endswith((".py", ".js", ".ts", ".tsx")) for file in changed_files):
        checklist.append("Review error handling and edge cases in changed code.")
    if any(
        file.endswith((".json", ".toml", ".yml", ".yaml")) for file in changed_files
    ):
        checklist.append("Validate changed configuration files before merging.")
    return checklist
