from __future__ import annotations

from pathlib import Path

from wintersolve.modules.architecture import map_architecture

from .conftest import write


class TestMapArchitecture:
    def test_groups_by_top_level_directory_with_purposes(self, python_project: Path) -> None:
        sections = {section.name: section for section in map_architecture(python_project)}

        assert set(sections) == {"src", "tests"}
        assert sections["src"].purpose == "Application or library source code"
        assert sections["tests"].notable_files == ["tests/test_demo.py"]

    def test_root_files_are_not_areas(self, tmp_path: Path) -> None:
        write(tmp_path / "README.md", "# x\n")
        write(tmp_path / "setup.py", "")

        assert map_architecture(tmp_path) == []

    def test_unknown_directories_get_a_neutral_purpose(self, tmp_path: Path) -> None:
        write(tmp_path / "widgets" / "a.py", "")

        (section,) = map_architecture(tmp_path)

        assert section.purpose == "Project area detected from repository structure"

    def test_notable_files_prefer_shallow_paths(self, tmp_path: Path) -> None:
        write(tmp_path / "src" / "deep" / "er" / "z.py", "")
        write(tmp_path / "src" / "main.py", "")

        (section,) = map_architecture(tmp_path)

        assert section.notable_files == ["src/main.py", "src/deep/er/z.py"]

    def test_missing_root(self, tmp_path: Path) -> None:
        assert map_architecture(tmp_path / "missing") == []
