"""Architecture map: what each top-level area of a repository is probably for."""

from __future__ import annotations

from pathlib import Path

from wintersolve.models import ArchitectureSection
from wintersolve.project import walk_project

# Conventional directory names and the role they usually play. Anything else
# gets a neutral description rather than a guess.
PURPOSE_BY_NAME = {
    "src": "Application or library source code",
    "app": "Application entrypoints and routes",
    "apps": "Applications in a monorepo",
    "packages": "Packages in a monorepo",
    "lib": "Shared library code",
    "pkg": "Shared library code",
    "cmd": "Command-line entrypoints",
    "internal": "Private application code",
    "api": "API layer",
    "server": "Server-side code",
    "client": "Client-side code",
    "web": "Web frontend",
    "frontend": "Web frontend",
    "backend": "Backend services",
    "services": "Service implementations",
    "tests": "Automated tests",
    "test": "Automated tests",
    "spec": "Automated tests",
    "__tests__": "Automated tests",
    "docs": "Project documentation",
    "doc": "Project documentation",
    "examples": "Example inputs, outputs, or sample projects",
    "scripts": "Developer and automation scripts",
    "tools": "Developer tooling",
    "templates": "Reusable templates and prompts",
    "config": "Configuration files",
    "configs": "Configuration files",
    "infra": "Infrastructure definitions",
    "deploy": "Deployment configuration",
    "migrations": "Database migrations",
    "public": "Static assets served as-is",
    "static": "Static assets",
    "assets": "Design and media assets",
    "data": "Data files and fixtures",
    "notebooks": "Jupyter notebooks",
    ".github": "GitHub community and automation files",
}

MAX_SECTIONS = 20
MAX_NOTABLE_FILES = 8


def map_architecture(root: Path) -> list[ArchitectureSection]:
    """Group files by top-level directory and describe each group."""
    tree = walk_project(root)
    files_by_area: dict[str, list[str]] = {}
    for project_file in tree.files:
        top_level, separator, _ = project_file.relative_path.partition("/")
        if not separator:
            continue  # Files at the root are listed elsewhere; not an "area".
        files_by_area.setdefault(top_level, []).append(project_file.relative_path)

    sections = [
        ArchitectureSection(
            name=name,
            path=name,
            purpose=PURPOSE_BY_NAME.get(name, "Project area detected from repository structure"),
            notable_files=_notable(files),
        )
        for name, files in sorted(files_by_area.items())
    ]
    return sections[:MAX_SECTIONS]


def _notable(files: list[str]) -> list[str]:
    # Shallow files describe an area better than deeply nested ones.
    return sorted(files, key=lambda path: (path.count("/"), path))[:MAX_NOTABLE_FILES]
