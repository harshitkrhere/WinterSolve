"""Regressions for changing and hostile repository trees."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from wintersolve.cli import _run, app
from wintersolve.modules import brain
from wintersolve.modules.brain import build_brain_report
from wintersolve.modules.security import _run_bandit, analyze_security
from wintersolve.project import read_text_file, walk_project

from .conftest import write


def test_next_recovery_build_is_pruned(tmp_path: Path) -> None:
    write(tmp_path / ".next-recovery-e2e" / "static" / "chunks" / "page.js", "eval(x)")
    write(tmp_path / "app" / "page.tsx", "export default function Page() {}")

    tree = walk_project(tmp_path)

    assert [file.relative_path for file in tree.files] == ["app/page.tsx"]
    assert analyze_security(tmp_path, run_bandit=False).files_checked == 1


def test_disappearing_file_marks_partial_and_continues(tmp_path: Path) -> None:
    vanished = write(tmp_path / "a.py", "x = 1")
    write(tmp_path / "b.py", "eval(x)")
    tree = walk_project(tmp_path)
    vanished.unlink()

    summary = analyze_security(tmp_path, tree=tree, run_bandit=False)

    assert summary.status == "attention needed"
    assert summary.files_checked == 1
    assert summary.skipped_reasons == {"file disappeared or unreadable": 1}
    assert [finding.path for finding in summary.findings] == ["b.py"]
    assert "Incomplete coverage" in " ".join(summary.notes)


def test_permission_error_without_findings_is_not_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(tmp_path / "locked.py", "x = 1")
    original = read_text_file

    def deny(path: Path, *, max_bytes: int | None = None) -> str:
        if path.name == "locked.py":
            raise PermissionError("locked")
        return original(path, max_bytes=max_bytes)

    monkeypatch.setattr("wintersolve.modules.security.read_text_file", deny)

    summary = analyze_security(tmp_path, run_bandit=False)

    assert summary.status == "partial"
    assert summary.files_checked == 0
    assert summary.skipped_files == 1


def test_large_and_invalid_utf8_files_report_coverage(tmp_path: Path) -> None:
    write(tmp_path / "oversized.py", "x" * 250_001)
    (tmp_path / "bad.py").write_bytes(b"x = '\xff'\n")

    summary = analyze_security(tmp_path, run_bandit=False)

    assert summary.status == "partial"
    assert summary.skipped_reasons == {
        "invalid UTF-8 bytes replaced": 1,
        "text file over size limit": 1,
    }


def test_file_changed_between_check_and_open_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = write(tmp_path / "changing.py", "x = 1")
    original_open = os.open

    def change_then_open(path: Path, flags: int) -> int:
        target.write_text("much longer content", encoding="utf-8")
        return original_open(path, flags)

    monkeypatch.setattr("wintersolve.project.os.open", change_then_open)

    with pytest.raises(OSError, match="changed before reading"):
        read_text_file(target)


def test_file_growth_limit_is_enforced(tmp_path: Path) -> None:
    target = write(tmp_path / "large.py", "x" * 20)

    with pytest.raises(OSError, match="size limit"):
        read_text_file(target, max_bytes=10)


def test_unicode_and_spaces_in_paths(tmp_path: Path) -> None:
    write(tmp_path / "src" / "üser data.py", "x = 1")

    tree = walk_project(tmp_path)

    assert [file.relative_path for file in tree.files] == ["src/üser data.py"]
    assert analyze_security(tmp_path, run_bandit=False).files_checked == 1


def test_large_fixture_excludes_generated_files(tmp_path: Path) -> None:
    for index in range(1000):
        write(tmp_path / ".next-recovery-e2e" / f"chunk{index}.js", "eval(x)")
        write(tmp_path / "apps" / f"page{index}.tsx", "export const x = 1")

    report = build_brain_report(tmp_path, run_bandit=False)

    assert report.security.files_checked == 1000
    assert report.security.findings == []
    assert report.source_paths == ["apps"]


def test_concurrent_security_reads_match_serial(tmp_path: Path) -> None:
    for index in range(128):
        write(tmp_path / f"file{index}.py", "eval(x)\n" if index == 64 else "x = 1\n")

    serial = analyze_security(tmp_path, run_bandit=False, read_workers=1)
    concurrent = analyze_security(tmp_path, run_bandit=False, read_workers=8)

    assert serial == concurrent


def test_invalid_security_worker_count_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="read_workers"):
        analyze_security(tmp_path, run_bandit=False, read_workers=0)


def test_symlink_outside_root_is_never_read(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = write(tmp_path / "outside.py", "eval(x)")
    link = project / "linked.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks unavailable")

    tree = walk_project(project)

    assert tree.files == []
    assert tree.skipped == {"linked file": 1}
    assert analyze_security(project, run_bandit=False).status == "partial"
    with pytest.raises(OSError, match="regular project file"):
        read_text_file(link)


def test_directory_link_and_broken_link_are_skipped(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    write(outside / "secret.py", "eval(x)")
    try:
        (project / "linked").symlink_to(outside, target_is_directory=True)
        (project / "broken.py").symlink_to(tmp_path / "missing.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    tree = walk_project(project)

    assert tree.files == []
    assert tree.skipped == {"linked directory": 1, "linked file": 1}


@pytest.mark.skipif(os.name != "nt", reason="Windows junctions only")
def test_windows_junction_does_not_expand_scope(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    write(outside / "secret.py", "eval(x)")
    link = project / "junction"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        pytest.skip("junction creation unavailable")
    try:
        tree = walk_project(project)
        assert tree.files == []
        assert tree.skipped == {"linked directory": 1}
    finally:
        link.rmdir()


def test_brain_uses_one_repository_walk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(tmp_path / "src" / "main.py", "x = 1")
    original = walk_project
    calls = 0

    def count(root: Path):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return original(root)

    monkeypatch.setattr(brain, "walk_project", count)
    monkeypatch.setattr(
        "wintersolve.modules.scanner.walk_project",
        lambda _root: pytest.fail("scanner repeated the walk"),
    )
    monkeypatch.setattr(
        "wintersolve.modules.security.walk_project",
        lambda _root: pytest.fail("security repeated the walk"),
    )
    monkeypatch.setattr(
        "wintersolve.modules.architecture.walk_project",
        lambda _root: pytest.fail("architecture repeated the walk"),
    )

    build_brain_report(tmp_path, run_bandit=False)

    assert calls == 1


def test_bandit_timeout_marks_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(tmp_path / "app.py", "x = 1")
    monkeypatch.setattr(
        "wintersolve.modules.security.importlib.util.find_spec", lambda _name: object()
    )

    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired("bandit", 120)

    monkeypatch.setattr("wintersolve.modules.security.subprocess.run", timeout)

    summary = analyze_security(tmp_path)

    assert summary.status == "partial"
    assert summary.skipped_reasons == {"Bandit analysis incomplete": 1}
    assert summary.skipped_files == 0


def test_bandit_error_marks_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(tmp_path / "app.py", "x = 1")
    monkeypatch.setattr(
        "wintersolve.modules.security.importlib.util.find_spec", lambda _name: object()
    )
    monkeypatch.setattr(
        "wintersolve.modules.security.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 2, '{"results":[]}', "failure"),
    )

    summary = analyze_security(tmp_path)

    assert summary.status == "partial"
    assert any("Bandit reported errors" in note for note in summary.notes)


def test_bandit_rechecks_discovered_python_files(tmp_path: Path) -> None:
    path = write(tmp_path / "removed.py", "x = 1")
    path.unlink()

    findings, note, complete = _run_bandit(tmp_path, [path])

    assert findings == []
    assert not complete
    assert "changed or became unreadable" in note


def test_missing_optional_bandit_is_reported_as_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(tmp_path / "app.py", "x = 1")
    monkeypatch.setattr("wintersolve.modules.security.importlib.util.find_spec", lambda _name: None)

    summary = analyze_security(tmp_path)

    assert summary.status == "partial"
    assert summary.skipped_reasons == {"Bandit analysis incomplete": 1}
    assert summary.skipped_files == 0


def test_brain_json_stdout_stays_clean_with_progress(tmp_path: Path, runner: CliRunner) -> None:
    write(tmp_path / "app.py", "x = 1")

    result = runner.invoke(app, ["brain", str(tmp_path), "--no-bandit", "--progress", "-f", "json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["identity"]["exists"]
    assert "Discovering files" in result.stderr


def test_keyboard_interrupt_exits_130() -> None:
    def interrupt() -> None:
        raise KeyboardInterrupt

    with pytest.raises(typer.Exit) as raised:
        _run(interrupt)

    assert raised.value.exit_code == 130
