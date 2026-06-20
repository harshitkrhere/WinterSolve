from __future__ import annotations

from pathlib import Path

from wintersolve.models import ArchitectureSection
from wintersolve.project import iter_project_files

PURPOSE_BY_NAME = {
    "src": "Application or library source code",
    "app": "Application entrypoints and routes",
    "lib": "Shared library code",
    "tests": "Automated tests",
    "test": "Automated tests",
    "docs": "Project documentation",
    ".github": "GitHub community and automation files",
    "scripts": "Developer and automation scripts",
    "templates": "Reusable templates and prompts",
    "examples": "Example inputs, outputs, or sample projects",
}


def map_architecture(root: Path) -> list[ArchitectureSection]:
    if not root.exists() or not root.is_dir():
        return []

    files = iter_project_files(root)
    by_top_level: dict[str, list[str]] = {}
    for project_file in files:
        top = project_file.relative_path.split("/", 1)[0]
        by_top_level.setdefault(top, []).append(project_file.relative_path)

    sections: list[ArchitectureSection] = []
    for name, section_files in sorted(by_top_level.items()):
        if len(section_files) == 1 and "/" not in section_files[0]:
            continue
        sections.append(
            ArchitectureSection(
                name=name,
                path=name,
                purpose=PURPOSE_BY_NAME.get(
                    name, "Project area detected from repository structure"
                ),
                notable_files=section_files[:8],
            )
        )
    return sections[:20]
