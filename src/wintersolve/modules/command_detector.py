"""Guess the commands a developer needs: install, build, test, run.

Sources, in order of trust: package manifests (high confidence), well-known
tool conventions (medium), and commands quoted in the README (medium).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from wintersolve.models import CommandCandidate
from wintersolve.project import read_text_file

MAX_PACKAGE_SCRIPTS = 10
MAX_COMMANDS = 25

# Lines in a README that start like this are probably commands worth repeating.
README_COMMAND_PREFIXES = (
    "python -m ",
    "python3 -m ",
    "pip install",
    "pipx install",
    "uv ",
    "poetry ",
    "pytest",
    "npm ",
    "npx ",
    "pnpm ",
    "yarn ",
    "bun ",
    "go build",
    "go run",
    "go test",
    "cargo ",
    "make ",
    "docker ",
    "gradle ",
    "./gradlew ",
    "mvn ",
    "dotnet ",
)

# Commands that show up in READMEs but are setup noise rather than workflow.
README_COMMAND_NOISE = ("python -m venv", "python3 -m venv", "pip install --upgrade pip")

MAKEFILE_TARGET = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*)\s*:(?!=)")

# ``pip install x   # explanation`` -> ``pip install x``
TRAILING_COMMENT = re.compile(r"\s+#.*$")


def detect_commands(root: Path) -> list[CommandCandidate]:
    """Return de-duplicated command candidates for the project at ``root``."""
    commands: list[CommandCandidate] = []
    commands.extend(_package_json_commands(root))
    commands.extend(_python_commands(root))
    commands.extend(_conventional_commands(root))
    commands.extend(_makefile_commands(root / "Makefile"))
    commands.extend(_readme_commands(root / "README.md"))
    return _dedupe(commands)


def _package_json_commands(root: Path) -> list[CommandCandidate]:
    manifest = root / "package.json"
    if not manifest.exists():
        return []

    runner = _node_package_manager(root)
    commands = [
        CommandCandidate(
            name="install",
            command=f"{runner} install",
            source="package.json",
            confidence="high",
        )
    ]
    try:
        data = json.loads(read_text_file(manifest))
    except json.JSONDecodeError:
        return commands

    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    if not isinstance(scripts, dict):
        return commands
    for name in list(scripts)[:MAX_PACKAGE_SCRIPTS]:
        run_prefix = runner if runner == "yarn" else f"{runner} run"
        commands.append(
            CommandCandidate(
                name=name,
                command=f"{run_prefix} {name}",
                source="package.json",
                confidence="high",
            )
        )
    return commands


def _node_package_manager(root: Path) -> str:
    """Pick the package manager from the lockfile that was committed."""
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lock").exists() or (root / "bun.lockb").exists():
        return "bun"
    return "npm"


def _python_commands(root: Path) -> list[CommandCandidate]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        if (root / "requirements.txt").exists():
            return [
                CommandCandidate(
                    name="install",
                    command="python -m pip install -r requirements.txt",
                    source="requirements.txt",
                    confidence="medium",
                )
            ]
        return []

    text = read_text_file(pyproject)
    commands: list[CommandCandidate] = []
    if (root / "uv.lock").exists():
        commands.append(CommandCandidate("install", "uv sync", "uv.lock", "high"))
        test_command = "uv run pytest"
    elif (root / "poetry.lock").exists() or "[tool.poetry]" in text:
        commands.append(CommandCandidate("install", "poetry install", "pyproject.toml", "high"))
        test_command = "poetry run pytest"
    else:
        commands.append(
            CommandCandidate(
                "install editable", "python -m pip install -e .", "pyproject.toml", "medium"
            )
        )
        test_command = "python -m pytest"

    uses_pytest = re.search(r"(?i)\bpytest\b", text) is not None
    commands.append(
        CommandCandidate(
            name="test",
            command=test_command if uses_pytest else "python -m unittest discover -s tests",
            source="pyproject.toml",
            confidence="medium",
        )
    )
    return commands


def _conventional_commands(root: Path) -> list[CommandCandidate]:
    """Commands implied by a tool's presence, without reading its config."""
    conventions: list[tuple[str, list[tuple[str, str]]]] = [
        ("go.mod", [("build", "go build ./..."), ("test", "go test ./...")]),
        ("Cargo.toml", [("build", "cargo build"), ("test", "cargo test")]),
        ("pom.xml", [("test", "mvn test"), ("package", "mvn package")]),
        ("build.gradle", [("test", "./gradlew test"), ("build", "./gradlew build")]),
        ("build.gradle.kts", [("test", "./gradlew test"), ("build", "./gradlew build")]),
        ("Gemfile", [("install", "bundle install")]),
        ("composer.json", [("install", "composer install")]),
        ("mix.exs", [("install", "mix deps.get"), ("test", "mix test")]),
        ("pubspec.yaml", [("install", "flutter pub get"), ("test", "flutter test")]),
        ("Pipfile", [("install", "pipenv install")]),
        (".pre-commit-config.yaml", [("lint", "pre-commit run --all-files")]),
        ("tox.ini", [("test matrix", "tox")]),
        ("noxfile.py", [("test matrix", "nox")]),
        ("justfile", [("list tasks", "just --list")]),
        ("Justfile", [("list tasks", "just --list")]),
        ("Taskfile.yml", [("list tasks", "task --list")]),
        ("docker-compose.yml", [("run services", "docker compose up")]),
        ("docker-compose.yaml", [("run services", "docker compose up")]),
        ("compose.yaml", [("run services", "docker compose up")]),
        ("compose.yml", [("run services", "docker compose up")]),
        ("Dockerfile", [("build image", f"docker build -t {root.name.lower()} .")]),
    ]
    commands: list[CommandCandidate] = []
    for marker, entries in conventions:
        if (root / marker).exists():
            commands.extend(
                CommandCandidate(name=name, command=command, source=marker, confidence="medium")
                for name, command in entries
            )
    return commands


def _makefile_commands(path: Path) -> list[CommandCandidate]:
    if not path.exists():
        return []
    commands: list[CommandCandidate] = []
    for line in read_text_file(path).splitlines():
        match = MAKEFILE_TARGET.match(line)
        if not match:
            continue
        target = match.group(1)
        if target.startswith(".") or "%" in target or "$" in target:
            continue  # Special targets and pattern rules are not user commands.
        commands.append(
            CommandCandidate(
                name=target, command=f"make {target}", source="Makefile", confidence="high"
            )
        )
    return commands


def _readme_commands(path: Path) -> list[CommandCandidate]:
    """Collect commands from fenced code blocks in the README.

    Prose is ignored on purpose: "pytest is our test runner" is a sentence,
    not a command.
    """
    if not path.exists():
        return []
    commands: list[CommandCandidate] = []
    in_code_block = False
    for raw_line in read_text_file(path).splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            continue
        if line.startswith("$ "):
            line = line[2:].strip()
        line = TRAILING_COMMENT.sub("", line)
        if not line.startswith(README_COMMAND_PREFIXES) or line.startswith(README_COMMAND_NOISE):
            continue
        commands.append(
            CommandCandidate(
                name=line.split()[0],
                command=line,
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
        if key not in seen:
            seen.add(key)
            unique.append(command)
    return unique[:MAX_COMMANDS]
