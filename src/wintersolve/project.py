from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "env",
}

TEXT_EXTENSIONS = {
    ".cfg",
    ".css",
    ".csv",
    ".env",
    ".go",
    ".graphql",
    ".h",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

MAX_TEXT_FILE_BYTES = 250_000


@dataclass(frozen=True)
class ProjectFile:
    path: Path
    relative_path: str
    size: int


def iter_project_files(root: Path) -> list[ProjectFile]:
    files: list[ProjectFile] = []
    if not root.exists() or not root.is_dir():
        return files

    for item in root.rglob("*"):
        if is_ignored(item, root) or not item.is_file():
            continue
        try:
            size = item.stat().st_size
        except OSError:
            continue
        files.append(
            ProjectFile(
                path=item,
                relative_path=item.relative_to(root).as_posix(),
                size=size,
            )
        )
    return sorted(files, key=lambda file: file.relative_path)


def is_ignored(item: Path, root: Path) -> bool:
    try:
        relative_parts = item.relative_to(root).parts
    except ValueError:
        return True
    return any(part in IGNORED_DIRECTORIES for part in relative_parts)


def is_probably_text(path: Path, size: int | None = None) -> bool:
    if size is not None and size > MAX_TEXT_FILE_BYTES:
        return False
    if path.name in {".gitignore", ".env.example"}:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def resolve_project_path(root: Path, candidate: str) -> Path:
    target = (root / candidate).resolve()
    if not _is_relative_to(target, root.resolve()):
        raise ValueError(f"Path is outside the project: {candidate}")
    return target


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

