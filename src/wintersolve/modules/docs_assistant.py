"""Documentation health: which README sections and hygiene files are missing.

Sections are detected from Markdown headings, so a README that *mentions*
"testing" in a sentence does not get credit for a Testing section, and one
titled "Getting Started" does get credit for Installation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from wintersolve.modules.scanner import ScanResult, scan_project

MAX_SECTION_SUGGESTIONS = 8

# Canonical section name -> words that count as that section when they appear
# in a heading. Matching is case-insensitive.
EXPECTED_README_SECTIONS: dict[str, tuple[str, ...]] = {
    "Overview": ("overview", "about", "introduction", "what is", "what it does", "why"),
    "Features": ("features", "what you get", "highlights", "capabilities", "commands"),
    "Installation": ("install", "getting started", "setup", "set up", "quick start", "quickstart"),
    "Usage": (
        "usage",
        "how to use",
        "examples",
        "quick start",
        "quickstart",
        "getting started",
        "try it",
    ),
    "Development": ("development", "developing", "hacking", "local setup", "contributors"),
    "Testing": ("testing", "tests", "running tests", "test suite"),
    "Contributing": ("contributing", "contribute", "contribution"),
    "Security": ("security", "vulnerability", "reporting"),
    "License": ("license", "licence"),
}

HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class DocsSuggestion:
    path: Path
    missing_sections: list[str]
    suggestions: list[str]
    readme_draft: str


def suggest_docs(path: Path, scan: ScanResult | None = None) -> DocsSuggestion:
    """Check README structure and hygiene files, and draft a README skeleton."""
    if scan is None:
        scan = scan_project(path)
    readme_path = path / "README.md"
    readme_text = (
        readme_path.read_text(encoding="utf-8", errors="replace") if readme_path.exists() else ""
    )

    headings = readme_headings(readme_text)
    missing_sections = [
        section
        for section, keywords in EXPECTED_README_SECTIONS.items()
        if not any(keyword in heading for heading in headings for keyword in keywords)
    ]
    project_name = _detect_project_name(path.name, readme_text)

    return DocsSuggestion(
        path=path,
        missing_sections=missing_sections,
        suggestions=_build_suggestions(scan.missing_recommended_files, missing_sections),
        readme_draft=_build_readme_draft(project_name, scan.frameworks, scan.languages),
    )


def readme_headings(markdown: str) -> list[str]:
    """Return lower-cased heading texts, ignoring headings inside code fences."""
    headings: list[str] = []
    in_code_block = False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = HEADING.match(line)
        if match:
            headings.append(match.group(1).lower())
    return headings


def _build_suggestions(missing_files: list[str], missing_sections: list[str]) -> list[str]:
    suggestions = [
        f"Add a README section for {section}."
        for section in missing_sections[:MAX_SECTION_SUGGESTIONS]
    ]
    suggestions.extend(f"Add {name} for a healthier open-source project." for name in missing_files)
    return suggestions or ["Documentation looks healthy based on the offline checklist."]


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
        ", ".join(language for language, _ in languages[:4]) or "Add main languages here"
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
