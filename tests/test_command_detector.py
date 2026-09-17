from __future__ import annotations

from pathlib import Path

from wintersolve.modules.command_detector import detect_commands

from .conftest import write


def commands_of(root: Path) -> list[str]:
    return [candidate.command for candidate in detect_commands(root)]


class TestNodeProjects:
    def test_reads_package_scripts_with_detected_package_manager(self, node_project: Path) -> None:
        commands = commands_of(node_project)

        assert commands[:4] == ["pnpm install", "pnpm run dev", "pnpm run build", "pnpm run test"]

    def test_defaults_to_npm_and_uses_yarn_shorthand(self, tmp_path: Path) -> None:
        write(tmp_path / "package.json", '{"scripts": {"test": "jest"}}')
        assert commands_of(tmp_path) == ["npm install", "npm run test"]

        write(tmp_path / "yarn.lock", "")
        assert commands_of(tmp_path) == ["yarn install", "yarn test"]

    def test_broken_package_json_still_yields_install(self, tmp_path: Path) -> None:
        write(tmp_path / "package.json", "{not json")

        assert commands_of(tmp_path) == ["npm install"]


class TestPythonProjects:
    def test_pip_and_pytest_when_pytest_is_configured(self, python_project: Path) -> None:
        assert commands_of(python_project) == ["python -m pip install -e .", "python -m pytest"]

    def test_uv_lock_switches_to_uv(self, python_project: Path) -> None:
        write(python_project / "uv.lock", "")

        assert commands_of(python_project) == ["uv sync", "uv run pytest"]

    def test_poetry_is_recognised_from_pyproject(self, tmp_path: Path) -> None:
        write(tmp_path / "pyproject.toml", "[tool.poetry]\nname = 'x'\n")

        assert commands_of(tmp_path) == [
            "poetry install",
            "python -m unittest discover -s tests",
        ]

    def test_requirements_only_project(self, tmp_path: Path) -> None:
        write(tmp_path / "requirements.txt", "requests\n")

        assert commands_of(tmp_path) == ["python -m pip install -r requirements.txt"]


class TestOtherSources:
    def test_conventional_commands_for_go_and_docker(self, tmp_path: Path) -> None:
        write(tmp_path / "go.mod", "module demo\n")
        write(tmp_path / "Dockerfile", "FROM golang\n")

        assert commands_of(tmp_path) == [
            "go build ./...",
            "go test ./...",
            f"docker build -t {tmp_path.name.lower()} .",
        ]

    def test_makefile_targets_skip_special_and_pattern_rules(self, tmp_path: Path) -> None:
        write(
            tmp_path / "Makefile",
            ".PHONY: test\nCC := gcc\ntest:\n\tpytest\n%.o: %.c\n\t$(CC)\nlint: test\n\truff\n",
        )

        assert commands_of(tmp_path) == ["make test", "make lint"]

    def test_readme_commands_come_only_from_code_blocks(self, tmp_path: Path) -> None:
        write(
            tmp_path / "README.md",
            "pytest is our runner.\n\n```bash\n$ pip install demo\npython -m venv .venv\n"
            "python -m demo serve\n```\n",
        )

        assert commands_of(tmp_path) == ["pip install demo", "python -m demo serve"]

    def test_readme_trailing_comments_are_dropped(self, tmp_path: Path) -> None:
        write(tmp_path / "README.md", "```bash\npipx install demo   # or: pip install demo\n```\n")

        assert commands_of(tmp_path) == ["pipx install demo"]

    def test_duplicates_are_removed_case_insensitively(self, tmp_path: Path) -> None:
        write(tmp_path / "Makefile", "test:\n\tpytest\n")
        write(tmp_path / "README.md", "```\nmake test\nMAKE TEST\n```\n")

        assert commands_of(tmp_path) == ["make test"]

    def test_conventional_commands_for_python_tooling(self, tmp_path: Path) -> None:
        write(tmp_path / ".pre-commit-config.yaml", "repos: []\n")
        write(tmp_path / "tox.ini", "[tox]\n")
        write(tmp_path / "noxfile.py", "import nox\n")

        assert commands_of(tmp_path) == ["pre-commit run --all-files", "tox", "nox"]

    def test_conventional_commands_for_task_runners(self, tmp_path: Path) -> None:
        write(tmp_path / "justfile", "test:\n\tpytest\n")
        write(tmp_path / "Taskfile.yml", "version: '3'\n")

        assert commands_of(tmp_path) == ["just --list", "task --list"]
