from __future__ import annotations

from pathlib import Path

from wintersolve.modules.scanner import scan_project

from .conftest import write


class TestScanProject:
    def test_detects_python_project_health_signals(self, python_project: Path) -> None:
        result = scan_project(python_project)

        assert result.exists
        assert ("Python", 3) in result.languages
        assert "Python package" in result.frameworks
        assert "README.md" in result.important_files
        assert "tests" in result.likely_test_paths
        assert "src/demo" in result.likely_source_paths
        assert result.missing_recommended_files == ["CONTRIBUTING.md", "SECURITY.md"]

    def test_detects_node_stack_from_root_markers_only(self, node_project: Path) -> None:
        result = scan_project(node_project)

        assert result.frameworks == ["Next.js", "Node.js", "pnpm"]
        assert result.total_files == 5  # node_modules is pruned, not counted

    def test_detects_ci_and_tooling_markers(self, tmp_path: Path) -> None:
        write(tmp_path / ".github" / "workflows" / "ci.yml", "name: CI\n")
        write(tmp_path / ".pre-commit-config.yaml", "repos: []\n")
        write(tmp_path / "Dockerfile", "FROM python:3.12\n")

        result = scan_project(tmp_path)

        assert result.frameworks == ["Docker", "GitHub Actions", "pre-commit"]

    def test_source_paths_stop_at_three_levels(self, tmp_path: Path) -> None:
        write(tmp_path / "src" / "pkg" / "sub" / "deep" / "mod.py")

        result = scan_project(tmp_path)

        assert result.likely_source_paths == ["src", "src/pkg", "src/pkg/sub"]

    def test_reports_missing_directory(self, tmp_path: Path) -> None:
        result = scan_project(tmp_path / "definitely-missing")

        assert not result.exists
        assert result.total_files == 0
        assert result.risks
        assert result.missing_recommended_files == [
            "README.md",
            "CONTRIBUTING.md",
            "LICENSE",
            "SECURITY.md",
        ]

    def test_empty_directory_has_no_files_risk(self, empty_project: Path) -> None:
        result = scan_project(empty_project)

        assert "No files were found in the project directory." in result.risks
        assert "No obvious test files or test directories were detected." in result.risks

    def test_hygiene_files_are_matched_by_convention_not_exact_name(self, tmp_path: Path) -> None:
        # Flask ships LICENSE.txt and CHANGES.rst; Express ships Readme.md and History.md.
        write(tmp_path / "Readme.md", "# Demo\n")
        write(tmp_path / "LICENSE.txt", "MIT\n")
        write(tmp_path / "CHANGES.rst", "Changes\n=======\n")
        write(tmp_path / "contributing.rst", "How to help\n")

        result = scan_project(tmp_path)

        assert result.important_files == [
            "Readme.md",
            "contributing.rst",
            "LICENSE.txt",
            "CHANGES.rst",
        ]
        assert result.missing_recommended_files == ["SECURITY.md"]
        assert "No README was found, so onboarding may be difficult." not in result.risks

    def test_healthy_project_has_no_risks(self, python_project: Path) -> None:
        write(python_project / "CONTRIBUTING.md", "# Contributing\n")
        write(python_project / "SECURITY.md", "# Security\n")

        result = scan_project(python_project)

        assert result.risks == []

    def test_to_dict_is_json_friendly(self, python_project: Path) -> None:
        data = scan_project(python_project).to_dict()

        assert data["path"] == str(python_project)
        assert {"name": "Python", "files": 3} in data["languages"]
