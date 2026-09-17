"""Shared fixtures: small, realistic projects built in a temp directory.

Tests never scan the WinterSolve repository itself, so they stay fast and do
not change meaning when the repository does.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


def write(path: Path, content: str = "") -> Path:
    """Create ``path`` (and parents) with ``content``; return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    """A tidy Python package with README, tests, and a pyproject that mentions pytest."""
    write(tmp_path / "README.md", "# Demo\n\n## Usage\n\nRun it.\n")
    write(tmp_path / "LICENSE", "MIT\n")
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "demo"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
    )
    write(tmp_path / "src" / "demo" / "__init__.py", '"""Demo package."""\n')
    write(tmp_path / "src" / "demo" / "core.py", "import os\n\n\nclass Demo:\n    pass\n")
    write(tmp_path / "tests" / "test_demo.py", "def test_demo() -> None:\n    assert True\n")
    return tmp_path


@pytest.fixture
def node_project(tmp_path: Path) -> Path:
    """A pnpm-based Next.js style app, including a dynamic route with brackets."""
    write(
        tmp_path / "package.json",
        '{"name": "demo", "scripts": {"dev": "next dev", "build": "next build", "test": "vitest"}}',
    )
    write(tmp_path / "pnpm-lock.yaml", "lockfileVersion: 9\n")
    write(tmp_path / "next.config.js", "module.exports = {}\n")
    write(tmp_path / "app" / "users" / "[id]" / "page.tsx", "export default function Page() {}\n")
    write(tmp_path / "node_modules" / "left-pad" / "index.js", "module.exports = 1\n")
    write(tmp_path / "README.md", "# Demo\n")
    return tmp_path
