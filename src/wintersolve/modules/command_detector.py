from __future__ import annotations

import json
import re
from pathlib import Path

from wintersolve.models import CommandCandidate
from wintersolve.project import read_text_file


def detect_commands(root: Path) -> list[CommandCandidate]:
    commands: list[CommandCandidate] = []
    commands.extend(_package_json_commands(root / "package.json"))
    commands.extend(_pyproject_commands(root / "pyproject.toml"))
    commands.extend(_makefile_commands(root / "Makefile"))
    commands.extend(_readme_commands(root / "README.md"))
    return _dedupe(commands)


def _package_json_commands(path: Path) -> list[CommandCandidate]:
    if not path.exists():
        return []
    try:
        data = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return [
            CommandCandidate(
                name="package metadata",
                command="npm run",
                source="package.json",
                confidence="low",
            )
        ]

    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return []

    commands: list[CommandCandidate] = []
    for name in ["dev", "start", "build", "test", "lint", "format"]:
        if name in scripts:
            commands.append(
                CommandCandidate(
                    name=name,
                    command=f"npm run {name}",
                    source="package.json",
                    confidence="high",
                )
            )
    return commands


def _pyproject_commands(path: Path) -> list[CommandCandidate]:
    if not path.exists():
        return []
    commands = [
        CommandCandidate(
            name="install editable",
            command="python -m pip install -e .",
            source="pyproject.toml",
            confidence="medium",
        )
    ]
    text = read_text_file(path).lower()
    if "pytest" in text:
        commands.append(
            CommandCandidate(
                name="test",
                command="python -m pytest",
                source="pyproject.toml",
                confidence="medium",
            )
        )
    else:
        commands.append(
            CommandCandidate(
                name="test",
                command="python -m unittest discover -s tests",
                source="pyproject.toml",
                confidence="medium",
            )
        )
    return commands


def _makefile_commands(path: Path) -> list[CommandCandidate]:
    if not path.exists():
        return []
    commands: list[CommandCandidate] = []
    for line in read_text_file(path).splitlines():
        match = re.match(r"^([a-zA-Z0-9_.-]+):", line)
        if match and not line.startswith("\t"):
            name = match.group(1)
            if name not in {".PHONY"}:
                commands.append(
                    CommandCandidate(
                        name=name,
                        command=f"make {name}",
                        source="Makefile",
                        confidence="high",
                    )
                )
    return commands


def _readme_commands(path: Path) -> list[CommandCandidate]:
    if not path.exists():
        return []
    commands: list[CommandCandidate] = []
    for line in read_text_file(path).splitlines():
        stripped = line.strip()
        if stripped.startswith(("python -m ", "npm ", "pnpm ", "yarn ", "go test", "cargo ")):
            commands.append(
                CommandCandidate(
                    name="documented command",
                    command=stripped,
                    source="README.md",
                    confidence="medium",
                )
            )
    return commands


def _dedupe(commands: list[CommandCandidate]) -> list[CommandCandidate]:
    seen: set[str] = set()
    unique: list[CommandCandidate] = []
    for command in commands:
        key = command.command.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(command)
    return unique[:20]

