from __future__ import annotations

from pathlib import Path

import pytest

from wintersolve.project import (
    MAX_TEXT_FILE_BYTES,
    is_code_file,
    is_ignored_directory,
    is_probably_text,
    iter_project_files,
    resolve_project_path,
    walk_project,
)

from .conftest import write


class TestWalkProject:
    def test_prunes_dependency_and_cache_directories(self, node_project: Path) -> None:
        tree = walk_project(node_project)

        relative = [file.relative_path for file in tree.files]
        assert "app/users/[id]/page.tsx" in relative
        assert not any(path.startswith("node_modules") for path in relative)
        assert "node_modules" not in tree.directories

    def test_ignores_generated_directories_by_suffix(self, tmp_path: Path) -> None:
        write(tmp_path / "demo.egg-info" / "PKG-INFO", "Name: demo\n")
        write(tmp_path / "src" / "demo.py", "x = 1\n")

        tree = walk_project(tmp_path)

        assert [file.relative_path for file in tree.files] == ["src/demo.py"]
        assert tree.directories == ["src"]

    def test_uses_forward_slashes_and_sorted_output(self, tmp_path: Path) -> None:
        write(tmp_path / "b" / "two.py")
        write(tmp_path / "a" / "one.py")

        tree = walk_project(tmp_path)

        assert [file.relative_path for file in tree.files] == ["a/one.py", "b/two.py"]
        assert tree.directories == ["a", "b"]

    def test_missing_root_gives_empty_tree(self, tmp_path: Path) -> None:
        tree = walk_project(tmp_path / "missing")

        assert tree.files == []
        assert tree.directories == []

    def test_iter_project_files_matches_walk(self, python_project: Path) -> None:
        assert iter_project_files(python_project) == walk_project(python_project).files


class TestFileClassification:
    @pytest.mark.parametrize("name", [".git", "node_modules", ".venv", "__pycache__", "x.egg-info"])
    def test_ignored_directory_names(self, name: str) -> None:
        assert is_ignored_directory(name)

    def test_regular_directory_is_not_ignored(self) -> None:
        assert not is_ignored_directory("src")

    def test_text_detection_uses_extension_and_known_names(self) -> None:
        assert is_probably_text(Path("app.py"))
        assert is_probably_text(Path("Dockerfile"))
        assert is_probably_text(Path(".gitignore"))
        assert not is_probably_text(Path("logo.png"))

    def test_large_files_are_not_treated_as_text(self) -> None:
        assert not is_probably_text(Path("bundle.js"), size=MAX_TEXT_FILE_BYTES + 1)

    def test_code_files_exclude_prose_and_config(self) -> None:
        assert is_code_file(Path("main.go"))
        assert not is_code_file(Path("README.md"))
        assert not is_code_file(Path("config.yaml"))


class TestResolveProjectPath:
    def test_blocks_parent_escape(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="outside the project"):
            resolve_project_path(tmp_path, "../outside.py")

    def test_accepts_paths_inside_the_project(self, tmp_path: Path) -> None:
        target = write(tmp_path / "src" / "app.py")

        assert resolve_project_path(tmp_path, "src/app.py") == target.resolve()
