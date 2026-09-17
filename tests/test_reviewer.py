from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from wintersolve.modules.reviewer import _parse_changed_files, review_changes

from .conftest import write

GIT = shutil.which("git")


def git(root: Path, *args: str) -> None:
    subprocess.run([GIT or "git", *args], cwd=root, check=True, capture_output=True)


class TestParseChangedFiles:
    def test_handles_renames_quotes_and_blank_lines(self) -> None:
        status = ' M src/app.py\nR  old.py -> new.py\n?? "has space.md"\n\n'

        assert _parse_changed_files(status) == ["src/app.py", "new.py", "has space.md"]


@pytest.mark.skipif(GIT is None, reason="git not installed")
class TestReviewChanges:
    def test_reports_risks_and_checklist_for_dirty_repo(self, tmp_path: Path) -> None:
        git(tmp_path, "init", "-q")
        write(tmp_path / "app.py", "print('hi')\n")
        write(tmp_path / ".github" / "workflows" / "ci.yml", "name: CI\n")
        write(tmp_path / "README.md", "# Demo\n")

        result = review_changes(tmp_path)

        assert result.git_available
        assert result.changed_files == [".github/workflows/ci.yml", "README.md", "app.py"]
        assert (
            "Code files changed: tests or manual verification should be included." in result.risks
        )
        assert (
            "CI workflows changed: confirm permissions and secrets are still minimal."
            in result.risks
        )
        assert "Review error handling and edge cases in changed code." in result.checklist

    def test_clean_repo_has_no_changes(self, tmp_path: Path) -> None:
        git(tmp_path, "init", "-q")

        result = review_changes(tmp_path)

        assert result.changed_files == []
        assert result.risks == ["No local changes were detected."]


class TestWithoutGit:
    def test_non_repository_is_reported(self, tmp_path: Path) -> None:
        # A plain temp directory is not inside a repository, so git status fails.
        result = review_changes(tmp_path)

        assert not result.git_available
        assert result.checklist == ["Initialize Git or run this command inside a Git repository."]
