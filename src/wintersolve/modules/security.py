"""Offline security scan: leaked secrets, risky code patterns, and optional Bandit.

Three layers, each clearly labelled in the report so nobody mistakes a
heuristic for a verdict:

* ``secret``       - token formats with a known shape (AWS, GitHub, Stripe...)
                     plus a guarded "looks like a hardcoded password" rule.
* ``code-pattern`` - eval/exec, ``shell=True``, unsafe deserialization, and SQL
                     built from request data. Only applied to source files.
* ``bandit``       - Bandit's own findings for Python, if Bandit is installed.

Findings in test code are rated ``low``: tests call ``eval``, start debug
servers, and use fake passwords on purpose. A well-known token format stays
``high`` wherever it appears, because a real key in a test is still a leak.

Evidence lines are always redacted before they leave this module.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from pathlib import Path
from typing import Any

from wintersolve.logging_config import get_logger
from wintersolve.models import SecurityFinding, SecuritySummary
from wintersolve.project import (
    MAX_TEXT_FILE_BYTES,
    ProjectFile,
    ProjectTree,
    is_code_file,
    is_probably_text,
    is_test_path,
    read_text_file,
    walk_project,
)

logger = get_logger("wintersolve.modules.security")

CATEGORY_SECRET = "secret"
CATEGORY_CODE_PATTERN = "code-pattern"
CATEGORY_BANDIT = "bandit"

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

STATUS_CLEAR = "clear"
STATUS_LOW_ONLY = "low-severity findings only"
STATUS_ATTENTION = "attention needed"
STATUS_PARTIAL = "partial"
SKIPPED_FILE_REASONS = frozenset(
    {
        "inaccessible file metadata",
        "linked file",
        "special file",
        "text file over size limit",
        "file disappeared or unreadable",
    }
)

# Token formats that are unambiguous when they appear verbatim.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Anthropic API key", re.compile(r"\bsk-ant-api03-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("Stripe secret key", re.compile(r"\bsk_live_[a-zA-Z0-9]{20,}\b")),
    ("Slack bot token", re.compile(r"\bxoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}\b")),
    (
        "Slack user token",
        re.compile(r"\bxoxp-[0-9]{10,}-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}\b"),
    ),
    ("SendGrid API key", re.compile(r"\bSG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("PEM private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# ``password = "..."`` style assignments. The value is captured so the guard
# below can reject placeholders and code expressions.
GENERIC_SECRET_KIND = "Hardcoded secret-like value"
GENERIC_SECRET_PATTERN = re.compile(
    # Group 1: the whole variable name (``DB_PASSWORD``, ``stripe.secret_key``)
    # ending in a credential-ish word. Group 2: the assigned value.
    r"(?i)([A-Za-z0-9_.-]*?"
    r"(?:api[_-]?key|secret[_-]?key|access[_-]?key|private[_-]?key"
    r"|auth[_-]?token|access[_-]?token|secret|token|password|passwd|pwd))"
    r"\s*[:=]\s*['\"]?([^'\"\s,;]{12,})"
)

# Values that are clearly not real credentials.
PLACEHOLDER_HINTS = (
    "example",
    "placeholder",
    "changeme",
    "change-me",
    "your-",
    "your_",
    "xxxx",
    "dummy",
    "sample",
    "redacted",
    "<",
    ">",
    "...",
    "${",
    "{{",
    "%(",
)
# Values that are code, not literals: attribute access, calls, env lookups.
CODE_EXPRESSION_HINTS = ("(", ")", "self.", "os.", "process.", "config.", "settings.", "env")

# Risky constructs worth a second look. Applied only to source files.
# ``inspect_strings`` says whether the rule needs to see string literal contents:
# SQL lives inside strings, while a mention of ``eval(`` inside a string or a
# comment is documentation, not a call.
CODE_PATTERNS: list[tuple[str, re.Pattern[str], bool]] = [
    (
        "SQL built from request data",
        re.compile(
            r"(?i)(select|insert|update|delete|drop)\s+.*?\s*(?:from|into|table)\s+"
            r".*?(?:\+|%s|f\").*?(?:request|input|query|params|body|data)"
        ),
        True,
    ),
    ("eval() call", re.compile(r"(?<![\w.])eval\s*\("), False),
    ("exec() call", re.compile(r"(?<![\w.])exec\s*\("), False),
    (
        "Shell command with shell=True",
        re.compile(
            r"\b(os\.system|subprocess\.(Popen|run|call|check_output)\s*\(.*shell\s*=\s*True)"
        ),
        False,
    ),
    (
        "Unsafe deserialization",
        re.compile(r"\b(pickle\.loads?|yaml\.load|marshal\.loads?)\s*\("),
        False,
    ),
]

STRING_LITERAL = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")
LINE_COMMENT = re.compile(r"(#|//).*$")

BANDIT_TIMEOUT_SECONDS = 120
MAX_REPORTED_FINDINGS = 50
MAX_EVIDENCE_CHARS = 160
DEFAULT_READ_WORKERS = 8
MAX_READ_WORKERS = 32
READ_BATCH_FILES = 64
BANDIT_ARGV_MAX_CHARS = 15_000
BANDIT_BATCH_FILES = 200


def analyze_security(  # noqa: PLR0912, PLR0915 - orchestrates coverage and optional Bandit
    root: Path,
    *,
    run_bandit: bool = True,
    tree: ProjectTree | None = None,
    progress: Callable[[str, int | None], None] | None = None,
    read_workers: int = DEFAULT_READ_WORKERS,
) -> SecuritySummary:
    """Scan ``root`` for secrets and risky patterns; optionally run Bandit too."""
    tree = tree if tree is not None else walk_project(root)
    findings: list[SecurityFinding] = []
    files_checked = 0
    skipped = dict(tree.skipped)
    python_files = [file.path for file in tree.files if file.path.suffix == ".py"]

    if progress:
        progress("Scanning security patterns", 0)

    if read_workers < 1 or read_workers > MAX_READ_WORKERS:
        raise ValueError("read_workers must be between 1 and 32")

    def candidates() -> Iterator[ProjectFile]:
        for project_file in tree.files:
            if not is_probably_text(project_file.path):
                continue
            if not is_probably_text(project_file.path, project_file.size):
                skipped["text file over size limit"] = (
                    skipped.get("text file over size limit", 0) + 1
                )
                continue
            yield project_file

    pending = candidates()
    with ThreadPoolExecutor(max_workers=read_workers) as pool:
        while batch := list(islice(pending, READ_BATCH_FILES)):
            for project_file, text, error in pool.map(_read_security_candidate, batch):
                if error is not None:
                    logger.warning(
                        "Skipping unreadable file %s: %s", project_file.relative_path, error
                    )
                    skipped["file disappeared or unreadable"] = (
                        skipped.get("file disappeared or unreadable", 0) + 1
                    )
                    continue
                assert text is not None
                if "\ufffd" in text:
                    skipped["invalid UTF-8 bytes replaced"] = (
                        skipped.get("invalid UTF-8 bytes replaced", 0) + 1
                    )
                files_checked += 1
                findings.extend(
                    _scan_text(project_file.relative_path, text, is_code_file(project_file.path))
                )
                if progress and files_checked % 500 == 0:
                    progress("Scanning security patterns", files_checked)

    notes = [
        "Secret-like values are redacted before they appear in any report.",
        "Built-in checks inspect recognised text files up to 250,000 bytes; "
        "generated and dependency directories are excluded.",
    ]
    if run_bandit and python_files:
        if progress:
            progress("Running Bandit", len(python_files))
        bandit_findings, bandit_note, bandit_complete = _run_bandit(root, python_files)
        findings = _without_lines_bandit_also_found(findings, bandit_findings)
        findings.extend(bandit_findings)
        notes.append(bandit_note)
        if not bandit_complete:
            skipped["Bandit analysis incomplete"] = 1
    elif run_bandit:
        notes.append("Bandit skipped: no Python files found.")
    else:
        notes.append("Bandit skipped by request (--no-bandit).")

    total_findings = len(findings)
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 3), f.path, f.line))
    if total_findings > MAX_REPORTED_FINDINGS:
        notes.append(
            f"Showing the first {MAX_REPORTED_FINDINGS} of {total_findings} findings, "
            "highest severity first."
        )
        findings = findings[:MAX_REPORTED_FINDINGS]
    if any(finding.severity == "low" for finding in findings):
        notes.append(
            "Findings in test code are rated low: tests use eval, debug servers, "
            "and fake credentials on purpose."
        )
    if findings:
        notes.append("Treat findings as leads, not verdicts: confirm each one in context.")
    if skipped:
        notes.append(
            "Incomplete coverage: "
            + ", ".join(f"{reason} ({count})" for reason, count in sorted(skipped.items()))
            + "."
        )

    logger.info(
        "Security scan complete: %d files checked, %d findings", files_checked, len(findings)
    )
    return SecuritySummary(
        status=_status(findings)
        if not skipped or any(f.severity != "low" for f in findings)
        else STATUS_PARTIAL,
        offline_by_default=True,
        files_checked=files_checked,
        findings=findings,
        notes=notes,
        skipped_files=sum(
            count for reason, count in skipped.items() if reason in SKIPPED_FILE_REASONS
        ),
        skipped_reasons=skipped,
    )


def _read_security_candidate(
    project_file: ProjectFile,
) -> tuple[ProjectFile, str | None, OSError | None]:
    try:
        return project_file, read_text_file(project_file.path, max_bytes=MAX_TEXT_FILE_BYTES), None
    except OSError as error:
        return project_file, None, error


def _status(findings: list[SecurityFinding]) -> str:
    if any(finding.severity != "low" for finding in findings):
        return STATUS_ATTENTION
    return STATUS_LOW_ONLY if findings else STATUS_CLEAR


def _without_lines_bandit_also_found(
    findings: list[SecurityFinding], bandit_findings: list[SecurityFinding]
) -> list[SecurityFinding]:
    """Drop a code-pattern finding when Bandit flagged the same line.

    Bandit's version names the exact rule (``B307``), so it is the one to keep.
    """
    bandit_lines = {(finding.path, finding.line) for finding in bandit_findings}
    return [
        finding
        for finding in findings
        if not (
            finding.category == CATEGORY_CODE_PATTERN
            and (finding.path, finding.line) in bandit_lines
        )
    ]


def _scan_text(relative_path: str, text: str, is_code: bool) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    in_tests = is_test_path(relative_path)
    for line_number, line in enumerate(text.splitlines(), start=1):
        findings.extend(
            _scan_line(relative_path, line_number, line, is_code=is_code, in_tests=in_tests)
        )
    return findings


def _scan_line(
    relative_path: str, line_number: int, line: str, *, is_code: bool, in_tests: bool
) -> list[SecurityFinding]:
    """Apply every rule to one line and return the findings, evidence redacted."""
    findings: list[SecurityFinding] = []
    usual_severity = "low" if in_tests else "medium"

    def report(category: str, kind: str, severity: str) -> None:
        findings.append(
            SecurityFinding(
                path=relative_path,
                line=line_number,
                category=category,
                kind=kind,
                severity=severity,
                evidence=redact_secrets(line.strip())[:MAX_EVIDENCE_CHARS],
            )
        )

    secret_kind = _match_known_secret(line)
    if secret_kind:
        report(CATEGORY_SECRET, secret_kind, "high")  # A real token leaks wherever it is.
    else:
        generic = GENERIC_SECRET_PATTERN.search(line)
        if generic and looks_like_real_secret(generic.group(2)):
            report(CATEGORY_SECRET, GENERIC_SECRET_KIND, usual_severity)

    if is_code:
        code_only = strip_strings_and_comments(line)
        for kind, pattern, inspect_strings in CODE_PATTERNS:
            haystack = line if inspect_strings else code_only
            if pattern.search(haystack):
                report(CATEGORY_CODE_PATTERN, kind, usual_severity)
    return findings


def strip_strings_and_comments(line: str) -> str:
    """Blank out string literal contents and trailing comments on one line.

    Good enough for single-line heuristics; multi-line strings are not tracked.
    """
    without_strings = STRING_LITERAL.sub('""', line)
    return LINE_COMMENT.sub("", without_strings)


def _match_known_secret(line: str) -> str | None:
    """Return the label of the first well-known token format found in ``line``."""
    for kind, pattern in SECRET_PATTERNS:
        if pattern.search(line):
            return kind
    return None


def looks_like_real_secret(value: str) -> bool:
    """Guard for the generic rule: reject placeholders and code expressions.

    ``api_key = self.config.api_key`` and ``token = os.getenv("TOKEN")`` are
    references, not leaks. ``password = "changeme"`` is a placeholder. What is
    left is worth a look.
    """
    lowered = value.lower()
    if any(hint in lowered for hint in PLACEHOLDER_HINTS):
        return False
    if any(hint in lowered for hint in CODE_EXPRESSION_HINTS):
        return False
    # Real secrets mix character classes; a plain word almost never is one.
    has_digit = any(char.isdigit() for char in value)
    has_alpha = any(char.isalpha() for char in value)
    return has_digit and has_alpha


def _bandit_working_parent(root: Path) -> Path | None:
    """Choose a directory outside the target for Bandit's isolated child."""
    resolved_root = root.resolve()
    return next(
        (
            candidate
            for candidate in (Path(tempfile.gettempdir()), Path.home(), Path(sys.base_prefix))
            if candidate.is_dir() and not candidate.resolve().is_relative_to(resolved_root)
        ),
        None,
    )


def _bandit_targets(root: Path, python_files: list[Path]) -> tuple[list[Path], int]:
    """Recheck discovered paths before handing them to another process."""
    resolved_root = root.resolve()
    safe_files: list[Path] = []
    rejected_files = 0
    for path in python_files:
        try:
            info = path.lstat()
            safe = (
                stat.S_ISREG(info.st_mode)
                and not getattr(info, "st_file_attributes", 0) & 0x400
                and path.resolve().is_relative_to(resolved_root)
            )
        except OSError:
            safe = False
        if safe:
            safe_files.append(path)
        else:
            rejected_files += 1
    return safe_files, rejected_files


def _run_bandit(  # noqa: PLR0911, PLR0912 - incomplete outcomes have distinct reasons
    root: Path, python_files: list[Path]
) -> tuple[list[SecurityFinding], str, bool]:
    """Run Bandit on the project's Python files, if it is installed.

    Only medium and high severity issues are collected; low-severity notes
    (``assert`` in tests, ``import subprocess``) drown out real problems.
    """
    if importlib.util.find_spec("bandit") is None:
        return (
            [],
            "Bandit not installed; install with `pip install 'wintersolve[security]'`.",
            False,
        )

    # `python -m bandit` searches its working directory. When WinterSolve is
    # launched from the repository, a repository-owned bandit.py could run.
    # Keep the child outside the target and discard a project PYTHONPATH.
    safe_parent = _bandit_working_parent(root)
    if safe_parent is None:
        return [], "Bandit could not find a working directory outside the project.", False
    safe_env = os.environ.copy()
    safe_env.pop("PYTHONPATH", None)

    safe_files, rejected_files = _bandit_targets(root, python_files)
    if not safe_files:
        return [], "Bandit skipped: discovered Python files changed or became unreadable.", False

    # Explicit discovered paths give Bandit precisely the same filesystem scope
    # as the built-in walk. Bound each argv for Windows' command-line limit.
    prefix = [
        sys.executable,
        "-m",
        "bandit",
        "-q",
        "-f",
        "json",
        "-ll",
    ]
    batches: list[list[str]] = []
    batch: list[str] = []
    length = 0
    for path in safe_files:
        name = str(path)
        if batch and (
            length + len(name) > BANDIT_ARGV_MAX_CHARS or len(batch) >= BANDIT_BATCH_FILES
        ):
            batches.append(batch)
            batch = []
            length = 0
        batch.append(name)
        length += len(name) + 3
    if batch:
        batches.append(batch)

    findings: list[SecurityFinding] = []
    deadline = time.monotonic() + BANDIT_TIMEOUT_SECONDS
    try:
        isolated_cwd = tempfile.TemporaryDirectory(prefix="wintersolve-bandit-", dir=safe_parent)
    except OSError:
        return [], "Bandit could not create an isolated working directory.", False
    with isolated_cwd as safe_cwd:
        for batch in batches:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return (
                    findings,
                    f"Bandit exceeded its {BANDIT_TIMEOUT_SECONDS}s total limit.",
                    False,
                )
            try:
                completed = subprocess.run(
                    [*prefix, *batch],
                    capture_output=True,
                    text=True,
                    timeout=remaining,
                    check=False,
                    cwd=safe_cwd,
                    env=safe_env,
                )
                payload = json.loads(completed.stdout)
                if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                    return findings, "Bandit returned invalid JSON output.", False
                findings.extend(_bandit_finding(issue, root) for issue in payload["results"])
                if completed.returncode not in (0, 1) or payload.get("errors"):
                    return findings, "Bandit reported errors; its analysis is incomplete.", False
            except subprocess.TimeoutExpired:
                return (
                    findings,
                    f"Bandit exceeded its {BANDIT_TIMEOUT_SECONDS}s total limit.",
                    False,
                )
            except (OSError, ValueError, TypeError) as error:
                logger.debug("Bandit could not be run: %s", error)
                return findings, "Bandit could not be run or returned invalid output.", False
    note = f"Bandit ran on {len(safe_files)} Python files: {len(findings)} issue(s)."
    if rejected_files:
        note += f" {rejected_files} discovered Python file(s) changed or became unreadable."
    return findings, note, rejected_files == 0


def _bandit_finding(issue: dict[str, Any], root: Path) -> SecurityFinding:
    """One entry of Bandit's JSON ``results``, in WinterSolve's own shape."""
    path = _relative_to_root(str(issue.get("filename", "")), root)
    line = int(issue.get("line_number", 0))
    severity = "low" if is_test_path(path) else str(issue.get("issue_severity", "medium")).lower()
    evidence = redact_secrets(_flagged_line(str(issue.get("code", "")), line))
    return SecurityFinding(
        path=path,
        line=line,
        category=CATEGORY_BANDIT,
        kind=f"Bandit {issue.get('test_id', '')}: {issue.get('issue_text', '')}".strip(),
        severity=severity,
        evidence=evidence[:MAX_EVIDENCE_CHARS],
    )


def _flagged_line(code: str, line_number: int) -> str:
    """Bandit quotes numbered lines of context; keep only the line it flagged."""
    context = code.strip().splitlines()
    for numbered in context:
        number, _, source = numbered.strip().partition(" ")
        if number == str(line_number):
            return source.strip()
    return context[0].strip() if context else ""


def _relative_to_root(filename: str, root: Path) -> str:
    try:
        return Path(filename).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return filename


def redact_secrets(text: str) -> str:
    """Replace anything that looks like a credential so reports are safe to share."""
    redacted = text
    for _, pattern in SECRET_PATTERNS:
        redacted = pattern.sub("<redacted-secret>", redacted)
    return GENERIC_SECRET_PATTERN.sub(_redact_assignment, redacted)


def _redact_assignment(match: re.Match[str]) -> str:
    return f"{match.group(1)}=<redacted>"
