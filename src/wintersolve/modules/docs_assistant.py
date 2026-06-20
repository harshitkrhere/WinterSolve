from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wintersolve.modules.scanner import ScanResult, scan_project


@dataclass(frozen=True)
class DocsSuggestion:
    path: Path
    missing_sections: list[str]
    suggestions: list[str]
    readme_draft: str


EXPECTED_README_SECTIONS = [
    "Overview",
    "Features",
    "Installation",
    "Usage",
    "Development",
    "Testing",
    "Contributing",
    "Security",
    "License",
]


def suggest_docs(path: Path, scan: ScanResult | None = None) -> DocsSuggestion:
    if scan is None:
        scan = scan_project(path)
    readme_path = path / "README.md"
    readme_text = ""
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8", errors="replace")

    missing_sections = [
        section
        for section in EXPECTED_README_SECTIONS
        if section.lower() not in readme_text.lower()
    ]
    suggestions = _build_suggestions(scan.missing_recommended_files, missing_sections)
    project_name = _detect_project_name(path.name, readme_text)
    readme_draft = _build_readme_draft(project_name, scan.frameworks, scan.languages)

    return DocsSuggestion(
        path=path,
        missing_sections=missing_sections,
        suggestions=suggestions,
        readme_draft=readme_draft,
    )


def _build_suggestions(
    missing_files: list[str], missing_sections: list[str]
) -> list[str]:
    suggestions: list[str] = []
    for section in missing_sections[:8]:
        suggestions.append(f"Add a README section for {section}.")
    for file in missing_files:
        suggestions.append(f"Add {file} for a healthier open-source project.")
    return suggestions or [
        "Documentation looks healthy based on the offline checklist."
    ]


def _detect_project_name(default_name: str, readme_text: str) -> str:
    for line in readme_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or default_name
    return default_name


def _build_readme_draft(
    project_name: str,
    frameworks: list[str],
    languages: list[tuple[str, int]],
) -> str:
    stack = ", ".join(frameworks) if frameworks else "Add detected stack here"
    language_list = (
        ", ".join(language for language, _ in languages[:4])
        or "Add main languages here"
    )
    return f"""# {project_name}

## Overview

Describe what this project does and who it helps.

## Features

- Add the most important user-facing feature.
- Add the second important feature.
- Add the third important feature.

## Tech Stack

- Stack: {stack}
- Languages: {language_list}

## Installation

Add setup instructions here.

## Usage

Add common commands and examples here.

## Development

Explain how contributors can run the project locally.

## Testing

Explain how to run the test suite.

## Contributing

Link to CONTRIBUTING.md or explain how to contribute.

## Security

Link to SECURITY.md or explain how to report vulnerabilities.

## License

Add license details here.
"""
