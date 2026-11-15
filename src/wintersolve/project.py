"""Filesystem helpers shared by every analyzer.

Everything that touches the disk goes through this module, so the rules for
what to skip, what counts as text, and how large a file we are willing to read
live in exactly one place.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
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
IGNORED_DIRECTORY_PREFIXES = (".next-",)

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

# Community-standard files come in many spellings: ``README.rst``, ``LICENSE.txt``,
# ``Readme.md``, ``COPYING``, ``CHANGES.rst``. Canonical name -> accepted stems.
HYGIENE_FILE_STEMS = {
    "README": ("README",),
    "LICENSE": ("LICENSE", "LICENCE", "COPYING"),
    "CONTRIBUTING": ("CONTRIBUTING",),
    "SECURITY": ("SECURITY",),
    "CODE_OF_CONDUCT": ("CODE_OF_CONDUCT",),
    "CHANGELOG": ("CHANGELOG", "CHANGES", "HISTORY", "NEWS"),
}
# In order of preference when a project has more than one spelling.
HYGIENE_FILE_SUFFIXES = (".md", ".markdown", ".rst", ".txt", "")
# GitHub shows these community files from the root, ``.github/``, or ``docs/``,
# so a project that keeps CONTRIBUTING.md in ``.github/`` does have one.
# LICENSE and CHANGELOG are only conventional at the root.
COMMUNITY_FILE_FOLDERS = (".github", "docs")
ACCEPTED_OUTSIDE_ROOT = frozenset({"README", "CONTRIBUTING", "SECURITY", "CODE_OF_CONDUCT"})

# Where tests live, by directory name or file name.
TEST_DIRECTORY_NAMES = frozenset({"test", "tests", "spec", "__tests__"})
TEST_FILE_ENDINGS = (
    "_test.py",
    "_test.go",
    ".test.js",
    ".test.jsx",
    ".test.ts",
    ".test.tsx",
    ".spec.js",
    ".spec.jsx",
    ".spec.ts",
    ".spec.tsx",
    "_spec.rb",
)
TEST_PREFIX_EXTENSIONS = frozenset({".py", ".js", ".ts", ".tsx", ".go", ".rs", ".rb", ".java"})


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
    skipped: dict[str, int] = field(default_factory=dict)


def _is_reparse_point(info: os.stat_result) -> bool:
    """Windows junctions and other reparse points must not expand the walk."""
    return bool(getattr(info, "st_file_attributes", 0) & 0x400)


def walk_project(
    root: Path, *, progress: Callable[[str, int | None], None] | None = None
) -> ProjectTree:
    """Walk ``root`` once, skipping ignored directories entirely.

    Symbolic links to directories are not followed, which keeps the walk
    finite even in repositories with circular links.
    """
    files: list[ProjectFile] = []
    directories: list[str] = []
    if not root.is_dir():
        return ProjectTree(root=root, files=files, directories=directories)

    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    def on_error(_error: OSError) -> None:
        skip("inaccessible directory")

    for current, dirnames, filenames in os.walk(root, onerror=on_error):
        # Editing ``dirnames`` in place is how os.walk lets callers prune.
        current_path = Path(current)
        safe_dirs = []
        for name in dirnames:
            if is_ignored_directory(name):
                continue
            try:
                info = (current_path / name).lstat()
            except OSError:
                skip("inaccessible directory")
                continue
            if stat.S_ISLNK(info.st_mode) or _is_reparse_point(info):
                skip("linked directory")
                continue
            safe_dirs.append(name)
        dirnames[:] = sorted(safe_dirs)

        for name in dirnames:
            directories.append((current_path / name).relative_to(root).as_posix())

        for name in filenames:
            path = current_path / name
            try:
                info = path.lstat()
            except OSError:
                skip("inaccessible file metadata")
                continue
            if stat.S_ISLNK(info.st_mode) or _is_reparse_point(info):
                skip("linked file")
                continue
            if not stat.S_ISREG(info.st_mode):
                skip("special file")
                continue
            files.append(
                ProjectFile(
                    path=path, relative_path=path.relative_to(root).as_posix(), size=info.st_size
                )
            )
            if progress and len(files) % 500 == 0:
                progress("Discovering files", len(files))

    files.sort(key=lambda file: file.relative_path)
    directories.sort()
    return ProjectTree(root=root, files=files, directories=directories, skipped=skipped)


def iter_project_files(root: Path) -> list[ProjectFile]:
    """Return every analyzable file under ``root``, sorted by relative path."""
    return walk_project(root).files


def is_ignored_directory(name: str) -> bool:
    """Whether a directory *name* (not path) should be skipped during a walk."""
    return (
        name in IGNORED_DIRECTORIES
        or name.endswith(IGNORED_DIRECTORY_SUFFIXES)
        or name.startswith(IGNORED_DIRECTORY_PREFIXES)
    )


def find_hygiene_files(root_file_names: Iterable[str]) -> dict[str, str]:
    """Map canonical names (``README``, ``LICENSE``...) to the actual file at the root.

    Matching is case-insensitive and accepts the usual suffixes, so ``Readme.md``,
    ``README.rst`` and ``LICENSE.txt`` all count. When several spellings exist,
    Markdown wins because it is what the docs assistant reads best.
    """

    def preference(name: str) -> tuple[int, str]:
        suffix = Path(name).suffix.lower()
        rank = HYGIENE_FILE_SUFFIXES.index(suffix) if suffix in HYGIENE_FILE_SUFFIXES else 99
        return rank, name

    found: dict[str, str] = {}
    for name in sorted(root_file_names, key=preference):
        path = Path(name)
        if path.suffix.lower() not in HYGIENE_FILE_SUFFIXES:
            continue
        for canonical, stems in HYGIENE_FILE_STEMS.items():
            if path.stem.upper() in stems:
                found.setdefault(canonical, name)
    return found


def find_community_files(relative_files: Iterable[str]) -> dict[str, str]:
    """Like ``find_hygiene_files``, but for a whole project listing.

    Files at the root win. ``.github/`` and ``docs/`` are also searched for the
    files GitHub accepts there. Values are relative paths such as
    ``docs/contributing.rst``.
    """
    names_by_folder: dict[str, list[str]] = {}
    for relative_path in relative_files:
        folder, _, name = relative_path.rpartition("/")
        names_by_folder.setdefault(folder, []).append(name)

    found = find_hygiene_files(names_by_folder.get("", []))
    for folder in COMMUNITY_FILE_FOLDERS:
        for canonical, name in find_hygiene_files(names_by_folder.get(folder, [])).items():
            if canonical in ACCEPTED_OUTSIDE_ROOT:
                found.setdefault(canonical, f"{folder}/{name}")
    return found


def is_test_path(relative_path: str) -> bool:
    """Whether a file or directory is test code, judged by its directory or file name."""
    parts = relative_path.lower().split("/")
    name = parts[-1]
    return (
        any(part in TEST_DIRECTORY_NAMES for part in parts)
        or name.endswith(TEST_FILE_ENDINGS)
        or (name.startswith("test_") and Path(name).suffix in TEST_PREFIX_EXTENSIONS)
    )


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


def read_text_file(path: Path, *, max_bytes: int | None = None) -> str:
    """Read a file as UTF-8, replacing undecodable bytes instead of crashing."""
    # O_NOFOLLOW closes the final-component symlink race on POSIX. Windows
    # reparse points are checked before opening; a concurrent replacement can
    # still race that check on Windows, so callers must treat untrusted trees
    # accordingly.
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or _is_reparse_point(info):
        raise OSError(f"Not a regular project file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or _is_reparse_point(opened):
            raise OSError(f"Not a regular project file: {path}")
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
        ):
            raise OSError(f"File changed before reading: {path}")
        content = stream.read(max_bytes + 1 if max_bytes is not None else -1)
        if max_bytes is not None and len(content) > max_bytes:
            raise OSError(f"File grew beyond size limit: {path}")
        finished = os.fstat(stream.fileno())
        if (opened.st_size, opened.st_mtime_ns) != (finished.st_size, finished.st_mtime_ns):
            raise OSError(f"File changed while reading: {path}")
        return content.decode("utf-8", errors="replace")


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
