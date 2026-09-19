from __future__ import annotations

from pathlib import Path

from wintersolve.modules.docs_assistant import readme_headings, suggest_docs

from .conftest import write


class TestSuggestDocs:
    def test_sections_are_detected_from_headings_with_synonyms(self, tmp_path: Path) -> None:
        write(
            tmp_path / "README.md",
            "# Demo\n\n## What is this?\n\n## Getting Started\n\n## Running tests\n\n"
            "## Contributing\n\n## Licence\n",
        )

        result = suggest_docs(tmp_path)

        assert result.missing_sections == ["Features", "Development", "Security"]

    def test_mentions_in_prose_do_not_count(self, tmp_path: Path) -> None:
        write(tmp_path / "README.md", "# Demo\n\nSee the installation and usage notes below.\n")

        result = suggest_docs(tmp_path)

        assert "Installation" in result.missing_sections
        assert "Usage" in result.missing_sections

    def test_reads_readme_under_any_conventional_name(self, tmp_path: Path) -> None:
        write(tmp_path / "Readme.md", "# Express\n\n## Installation\n\n## Quick Start\n")

        result = suggest_docs(tmp_path)

        assert "Installation" not in result.missing_sections
        assert "Usage" not in result.missing_sections
        assert result.readme_draft.startswith("# Express\n")

    def test_understands_restructuredtext_headings(self, tmp_path: Path) -> None:
        write(
            tmp_path / "README.rst",
            "Flask\n=====\n\nA framework.\n\nA Simple Example\n----------------\n\nCode.\n\n"
            "Contributing\n~~~~~~~~~~~~\n\nHelp out.\n",
        )

        result = suggest_docs(tmp_path)

        assert "Usage" not in result.missing_sections
        assert "Contributing" not in result.missing_sections
        assert "Installation" in result.missing_sections
        assert result.readme_draft.startswith("# Flask\n")

    def test_underlined_markdown_headings_count_too(self) -> None:
        markdown = "Demo\n====\n\nIntro text.\n\nUsage\n-----\n\n- a list item\n---\n"

        assert readme_headings(markdown) == ["demo", "usage"]

    def test_headings_inside_code_blocks_are_ignored(self) -> None:
        markdown = "# Real\n\n```md\n## Not a heading\n```\n\n## Usage ##\n"

        assert readme_headings(markdown) == ["real", "usage"]

    def test_suggestions_and_draft(self, tmp_path: Path) -> None:
        write(tmp_path / "README.md", "# Demo\n")
        write(tmp_path / "package.json", "{}")

        result = suggest_docs(tmp_path)

        assert "Add a README section for Installation." in result.suggestions
        assert "Add LICENSE for a healthier open-source project." in result.suggestions
        assert result.readme_draft.startswith("# Demo\n")
        assert "- Stack: Node.js" in result.readme_draft

    def test_missing_readme_uses_directory_name(self, empty_project: Path) -> None:
        result = suggest_docs(empty_project)

        assert result.readme_draft.startswith(f"# {empty_project.name}\n")
        assert len(result.missing_sections) == 9

    def test_healthy_docs_message(self, tmp_path: Path) -> None:
        write(
            tmp_path / "README.md",
            "# Demo\n\n## Overview\n## Features\n## Installation\n## Usage\n## Development\n"
            "## Testing\n## Contributing\n## Security\n## License\n",
        )
        for name in ("CONTRIBUTING.md", "LICENSE", "SECURITY.md"):
            write(tmp_path / name, "x\n")

        assert suggest_docs(tmp_path).suggestions == [
            "Documentation looks healthy based on the offline checklist."
        ]
