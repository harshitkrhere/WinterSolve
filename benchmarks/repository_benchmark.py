"""Repeatable local benchmark; fixtures stay in a temporary directory.

Run with ``python benchmarks/repository_benchmark.py --sizes 1000 10000 50000 100000``.
Set PYTHONPATH to a checkout's ``src`` directory to compare revisions.
"""

from __future__ import annotations

import argparse
import inspect
import json
import platform
import tempfile
import time
import tracemalloc
from pathlib import Path

from wintersolve.modules.architecture import map_architecture
from wintersolve.modules.brain import build_brain_report
from wintersolve.modules.scanner import scan_project
from wintersolve.modules.security import _run_bandit, analyze_security
from wintersolve.project import is_probably_text, walk_project
from wintersolve.report import render_brain_report


def make_fixture(root: Path, count: int, *, python_source: bool = False) -> None:
    """40% analyzable files, 60% realistic generated/dependency files."""
    folders = [
        root / "src" / "app",
        root / "tests",
        root / "config",
        root / "docs",
        root / ".next-recovery-e2e" / "static" / "chunks",
        root / "node_modules" / "pkg" / "dist",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
    (root / "README.md").write_text("# Benchmark\n## Usage\n", encoding="utf-8")
    for index in range(count):
        bucket = index % 10
        if bucket == 0:
            if python_source:
                path = folders[0] / f"module_{index}.py"
                content = f"value_{index} = {index}\n"
            else:
                path = folders[0] / f"module_{index}.ts"
                content = f"export const value{index} = {index};\n"
        elif bucket == 1:
            path = folders[1] / f"module_{index}.test.ts"
            content = f"const expected = {index};\n"
        elif bucket == 2:  # noqa: PLR2004 - fixed fixture distribution
            path = folders[2] / f"config_{index}.json"
            content = '{"enabled": true}\n'
        elif bucket == 3:  # noqa: PLR2004 - fixed fixture distribution
            path = folders[3] / f"note_{index}.md"
            content = "# Documentation\n"
        elif bucket < 7:  # noqa: PLR2004 - fixed fixture distribution
            path = folders[4] / f"chunk_{index}.js"
            content = "/* generated chunk */\n"
        else:
            path = folders[5] / f"lib_{index}.js"
            content = "/* dependency */\n"
        path.write_text(content, encoding="utf-8")


def timed(operation):  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    value = operation()
    return value, round(time.perf_counter() - started, 4)


def supports_tree(function) -> bool:  # type: ignore[no-untyped-def]
    return "tree" in inspect.signature(function).parameters


def benchmark(root: Path, requested: int, *, run_bandit: bool) -> dict[str, object]:
    tree, discovery = timed(lambda: walk_project(root))
    _, metadata = timed(
        lambda: scan_project(root, tree=tree) if supports_tree(scan_project) else scan_project(root)
    )
    security, security_seconds = timed(
        lambda: (
            analyze_security(root, run_bandit=False, tree=tree)
            if supports_tree(analyze_security)
            else analyze_security(root, run_bandit=False)
        )
    )
    _, architecture = timed(
        lambda: (
            map_architecture(root, tree=tree)
            if supports_tree(map_architecture)
            else map_architecture(root)
        )
    )
    bandit_seconds: float | None = None
    if run_bandit:
        python_files = [file.path for file in tree.files if file.path.suffix == ".py"]
        if python_files:
            _, bandit_seconds = timed(
                lambda: (
                    _run_bandit(root, python_files)
                    if len(inspect.signature(_run_bandit).parameters) > 1
                    else _run_bandit(root)
                )
            )
    report, total = timed(lambda: build_brain_report(root, run_bandit=run_bandit))
    rendered, report_seconds = timed(lambda: render_brain_report(report, output_format="json"))
    tracemalloc.start()
    build_brain_report(root, run_bandit=False)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    bytes_processed = sum(
        file.size for file in tree.files if is_probably_text(file.path, file.size)
    )
    return {
        "requested_fixture_files": requested,
        "discovered_files": len(tree.files),
        "security_files_checked": security.files_checked,
        "bytes_eligible_for_security": bytes_processed,
        "discovery_seconds": discovery,
        "metadata_seconds": metadata,
        "built_in_security_seconds": security_seconds,
        "architecture_seconds": architecture,
        "bandit_seconds": bandit_seconds,
        "report_render_seconds": report_seconds,
        "total_brain_seconds": total,
        "peak_python_allocations_bytes": peak,
        "report_bytes": len(rendered.encode("utf-8")),
        "security_status": security.status,
    }


def benchmark_total_only(root: Path, requested: int) -> dict[str, object]:
    """Warm the cache once, then measure total time and peak allocations."""
    build_brain_report(root, run_bandit=False)
    tree = walk_project(root)
    report, total = timed(lambda: build_brain_report(root, run_bandit=False))
    tracemalloc.start()
    build_brain_report(root, run_bandit=False)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "requested_fixture_files": requested,
        "discovered_files": len(tree.files),
        "total_brain_seconds": total,
        "peak_python_allocations_bytes": peak,
        "report_bytes": len(render_brain_report(report, output_format="json").encode("utf-8")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 10000, 50000, 100000])
    parser.add_argument("--bandit", action="store_true")
    parser.add_argument("--python-source", action="store_true", help="Use Python source in fixture")
    parser.add_argument("--total-only", action="store_true", help="Measure warm full runs only")
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "python": platform.python_version(),
                "bandit_enabled": args.bandit,
            }
        ),
        flush=True,
    )
    for size in args.sizes:
        with tempfile.TemporaryDirectory(prefix="wintersolve-benchmark-") as temporary:
            root = Path(temporary)
            make_fixture(root, size, python_source=args.python_source)
            measurement = (
                benchmark_total_only(root, size)
                if args.total_only
                else benchmark(root, size, run_bandit=args.bandit)
            )
            print(json.dumps(measurement), flush=True)


if __name__ == "__main__":
    main()
