"""Offline security scan: leaked secrets, risky code patterns, and optional Bandit.

Three layers, each clearly labelled in the report so nobody mistakes a
heuristic for a verdict:

* ``secret``       - token formats with a known shape (AWS, GitHub, Stripe...)
                     plus a guarded "looks like a hardcoded password" rule.
* ``code-pattern`` - eval/exec, ``shell=True``, unsafe deserialization, and SQL
                     built from request data. Only applied to source files.
* ``bandit``       - Bandit's own findings for Python, if Bandit is installed.

Evidence lines are always redacted before they leave this module.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from wintersolve.logging_config import get_logger
from wintersolve.models import SecurityFinding, SecuritySummary
from wintersolve.project import (
    IGNORED_DIRECTORIES,
    is_code_file,
    is_probably_text,
    read_text_file,
    walk_project,
)

logger = get_logger("wintersolve.modules.security")

CATEGORY_SECRET = "secret"
CATEGORY_CODE_PATTERN = "code-pattern"
CATEGORY_BANDIT = "bandit"

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

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


def analyze_security(root: Path, *, run_bandit: bool = True) -> SecuritySummary:
    """Scan ``root`` for secrets and risky patterns; optionally run Bandit too."""
    tree = walk_project(root)
    findings: list[SecurityFinding] = []
    files_checked = 0
    python_files = 0

    for project_file in tree.files:
        if not is_probably_text(project_file.path, project_file.size):
            continue
        files_checked += 1
        if project_file.path.suffix == ".py":
            python_files += 1
        text = read_text_file(project_file.path)
        findings.extend(
            _scan_text(project_file.relative_path, text, is_code_file(project_file.path))
        )

    notes = ["Secret-like values are redacted before they appear in any report."]
    if run_bandit and python_files:
        bandit_findings, bandit_note = _run_bandit(root)
        findings.extend(bandit_findings)
        notes.append(bandit_note)
    elif run_bandit:
        notes.append("Bandit skipped: no Python files found.")
    else:
        notes.append("Bandit skipped by request (--no-bandit).")

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 3), f.path, f.line))
    if len(findings) > MAX_REPORTED_FINDINGS:
        notes.append(
            f"Showing the first {MAX_REPORTED_FINDINGS} of {len(findings)} findings, "
            "highest severity first."
        )
        findings = findings[:MAX_REPORTED_FINDINGS]
    if findings:
        notes.append("Treat findings as leads, not verdicts: confirm each one in context.")

    logger.info(
        "Security scan complete: %d files checked, %d findings", files_checked, len(findings)
    )
    return SecuritySummary(
        status="attention needed" if findings else "clear",
        offline_by_default=True,
        files_checked=files_checked,
        findings=findings,
        notes=notes,
    )


def _scan_text(relative_path: str, text: str, is_code: bool) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        findings.extend(_scan_line(relative_path, line_number, line, is_code=is_code))
    return findings


def _scan_line(
    relative_path: str, line_number: int, line: str, *, is_code: bool
) -> list[SecurityFinding]:
    """Apply every rule to one line and return the findings, evidence redacted."""
    findings: list[SecurityFinding] = []

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
        report(CATEGORY_SECRET, secret_kind, "high")
    else:
        generic = GENERIC_SECRET_PATTERN.search(line)
        if generic and looks_like_real_secret(generic.group(2)):
            report(CATEGORY_SECRET, GENERIC_SECRET_KIND, "medium")

    if is_code:
        code_only = strip_strings_and_comments(line)
        for kind, pattern, inspect_strings in CODE_PATTERNS:
            haystack = line if inspect_strings else code_only
            if pattern.search(haystack):
                report(CATEGORY_CODE_PATTERN, kind, "medium")
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


def _run_bandit(root: Path) -> tuple[list[SecurityFinding], str]:
    """Run Bandit on the project's Python files, if it is installed.

    Only medium and high severity issues are collected; low-severity notes
    (``assert`` in tests, ``import subprocess``) drown out real problems.
    """
    if importlib.util.find_spec("bandit") is None:
        return [], "Bandit not installed; install with `pip install 'wintersolve[security]'`."

    excludes = ",".join(sorted(IGNORED_DIRECTORIES))
    # ``-ll`` means "medium severity and above" and works on every Bandit release.
    command = [
        sys.executable,
        "-m",
        "bandit",
        "-q",
        "-r",
        "-f",
        "json",
        "-ll",
        "-x",
        excludes,
        str(root),
    ]
    try:
        completed = subprocess.run(  # fixed argv, never a shell
            command,
            capture_output=True,
            text=True,
            timeout=BANDIT_TIMEOUT_SECONDS,
            check=False,
        )
        payload = json.loads(completed.stdout or "{}")
    except subprocess.TimeoutExpired:
        return [], f"Bandit timed out after {BANDIT_TIMEOUT_SECONDS}s; run it manually for details."
    except (OSError, json.JSONDecodeError) as error:
        logger.debug("Bandit could not be run: %s", error)
        return [], "Bandit could not be run; run `bandit -r .` manually for details."

    findings = [
        SecurityFinding(
            path=_relative_to_root(str(issue.get("filename", "")), root),
            line=int(issue.get("line_number", 0)),
            category=CATEGORY_BANDIT,
            kind=f"Bandit {issue.get('test_id', '')}: {issue.get('issue_text', '')}".strip(),
            severity=str(issue.get("issue_severity", "medium")).lower(),
            evidence=redact_secrets(str(issue.get("code", "")).strip())[:MAX_EVIDENCE_CHARS],
        )
        for issue in payload.get("results", [])
    ]
    return findings, (
        f"Bandit ran on Python files (medium and high severity): {len(findings)} issue(s)."
    )


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
