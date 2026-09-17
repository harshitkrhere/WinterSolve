"""Filesystem helpers shared by every analyzer.

Everything that touches the disk goes through this module, so the rules for
what to skip, what counts as text, and how large a file we are willing to read
live in exactly one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Directories that are never worth analyzing: version control internals,
# caches, virtual environments, dependency trees, and build output. They are
# pruned during the walk, so a repository with a 200k-file ``node_modules``
# still scans in well under a second.
IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        ".cache",
        ".eggs",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "__pycache__",
        "node_modules",
        "bower_components",
        "vendor",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        "target",
        "out",
        "coverage",
        "htmlcov",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".turbo",
        ".parcel-cache",
        ".terraform",
        ".gradle",
        ".dart_tool",
        "Pods",
    }
)

# Generated directories are also recognisable by suffix (``wintersolve.egg-info``).
IGNORED_DIRECTORY_SUFFIXES = (".egg-info", ".dist-info")

# Programming and markup languages we count when describing a repository.
LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".cs": "C#",
    ".fs": "F#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".r": "R",
    ".jl": "Julia",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".m": "Objective-C",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".less": "CSS",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".tf": "Terraform",
}

# Structured data and configuration formats. Not "languages" for the language
# breakdown, but useful labels when explaining a single file.
DATA_FORMAT_BY_EXTENSION = {
    ".json": "JSON",
    ".jsonc": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".ini": "INI",
    ".cfg": "INI",
    ".env": "dotenv",
    ".csv": "CSV",
    ".txt": "Text",
    ".graphql": "GraphQL",
    ".proto": "Protocol Buffers",
}

# Extensions we are happy to open and read as UTF-8 text.
TEXT_EXTENSIONS = frozenset(LANGUAGE_BY_EXTENSION) | frozenset(DATA_FORMAT_BY_EXTENSION)

# Well-known files without an extension (or with an unusual one) that are text.
TEXT_FILENAMES = frozenset(
    {
        ".gitignore",
        ".gitattributes",
        ".dockerignore",
        ".editorconfig",
        ".env.example",
        ".env.sample",
        ".pre-commit-config.yaml",
        "Dockerfile",
        "Makefile",
        "Justfile",
        "justfile",
        "Procfile",
        "LICENSE",
        "CODEOWNERS",
    }
)

# Source-code extensions where "risky code pattern" heuristics make sense.
# Prose and config files are excluded so a README that *mentions* ``eval()``
# is not reported as a vulnerability.
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".vue",
        ".svelte",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".scala",
        ".cs",
        ".php",
        ".rb",
        ".swift",
        ".dart",
        ".ex",
        ".exs",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
    }
)

# Files larger than this are almost never hand-written source (bundles, fixtures,
# minified assets) and are skipped rather than read into memory.
MAX_TEXT_FILE_BYTES = 250_000


@dataclass(frozen=True)
class ProjectFile:
    """One file inside the project, with its path relative to the root."""

    path: Path
    relative_path: str
    size: int


@dataclass(frozen=True)
class ProjectTree:
    """Everything found under a project root once ignored directories are pruned.

    ``directories`` and ``files`` use forward-slash relative paths on every
    platform so reports and JSON are stable across operating systems.
    """

    root: Path
    files: list[ProjectFile]
    directories: list[str]


def walk_project(root: Path) -> ProjectTree:
    """Walk ``root`` once, skipping ignored directories entirely.

    Symbolic links to directories are not followed, which keeps the walk
    finite even in repositories with circular links.
    """
    files: list[ProjectFile] = []
    directories: list[str] = []
    if not root.is_dir():
        return ProjectTree(root=root, files=files, directories=directories)

    for current, dirnames, filenames in os.walk(root):
        # Editing ``dirnames`` in place is how os.walk lets callers prune.
        dirnames[:] = sorted(name for name in dirnames if not is_ignored_directory(name))
        current_path = Path(current)

        for name in dirnames:
            directories.append((current_path / name).relative_to(root).as_posix())

        for name in filenames:
            path = current_path / name
            try:
                size = path.stat().st_size
            except OSError:
                # Broken symlink or a file that vanished mid-scan. Not worth
                # failing the whole report over.
                continue
            files.append(
                ProjectFile(path=path, relative_path=path.relative_to(root).as_posix(), size=size)
            )

    files.sort(key=lambda file: file.relative_path)
    directories.sort()
    return ProjectTree(root=root, files=files, directories=directories)


def iter_project_files(root: Path) -> list[ProjectFile]:
    """Return every analyzable file under ``root``, sorted by relative path."""
    return walk_project(root).files


def is_ignored_directory(name: str) -> bool:
    """Whether a directory *name* (not path) should be skipped during a walk."""
    return name in IGNORED_DIRECTORIES or name.endswith(IGNORED_DIRECTORY_SUFFIXES)


def is_probably_text(path: Path, size: int | None = None) -> bool:
    """Cheap guess at whether a file can be read as text, without opening it."""
    if size is not None and size > MAX_TEXT_FILE_BYTES:
        return False
    if path.name in TEXT_FILENAMES or path.name.startswith(".env"):
        return True  # dotenv files (.env, .env.local, ...) are where secrets leak
    return path.suffix.lower() in TEXT_EXTENSIONS


def is_code_file(path: Path) -> bool:
    """Whether a file is source code (as opposed to prose, data, or config)."""
    return path.suffix.lower() in CODE_EXTENSIONS


def read_text_file(path: Path) -> str:
    """Read a file as UTF-8, replacing undecodable bytes instead of crashing."""
    return path.read_text(encoding="utf-8", errors="replace")


def resolve_project_path(root: Path, candidate: str) -> Path:
    """Resolve ``candidate`` and refuse anything that escapes ``root``.

    Used by commands that take a user-supplied file so that ``../../etc/passwd``
    style inputs are rejected instead of read.
    """
    resolved_root = root.resolve()
    target = (resolved_root / candidate).resolve()
    if not target.is_relative_to(resolved_root):
        raise ValueError(f"Path is outside the project: {candidate}")
    return target
