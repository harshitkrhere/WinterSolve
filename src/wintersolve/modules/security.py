from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from wintersolve.models import SecurityFinding, SecuritySummary
from wintersolve.project import is_probably_text, iter_project_files, read_text_file

SECRET_PATTERNS = [
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-api03-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("Stripe secret key", re.compile(r"\bsk_live_[a-zA-Z0-9]{20,}\b")),
    ("Slack bot token", re.compile(r"\bxoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}\b")),
    (
        "Slack user token",
        re.compile(r"\bxoxp-[0-9]{10,}-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}\b"),
    ),
    ("PEM private key", re.compile(r"-----BEGIN [A-Z]+ PRIVATE KEY-----")),
    ("SendGrid API key", re.compile(r"\bSG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b")),
    (
        "Generic assignment secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?([^'\"\s]{12,})"
        ),
    ),
]

HEURISTIC_PATTERNS = [
    (
        "SQL Injection Risk",
        re.compile(
            r"(?i)(select|insert|update|delete|drop)\s+.*?\s*(?:from|into|table)\s+.*?(?:\+|%s|f\").*?(?:request|input|query|params|body|data)"
        ),
    ),
    ("Eval Usage", re.compile(r"\beval\s*\(")),
    ("Exec Usage", re.compile(r"\bexec\s*\(")),
    (
        "Shell Injection Risk",
        re.compile(
            r"\b(os\.system|subprocess\.(Popen|run|call|check_output)\s*\(.*shell\s*=\s*True)"
        ),
    ),
    (
        "Unsafe Deserialization",
        re.compile(r"\b(pickle\.loads?|yaml\.load|marshal\.loads?)\s*\("),
    ),
]


def analyze_security(root: Path) -> SecuritySummary:
    findings: list[SecurityFinding] = []
    files_checked = 0

    for project_file in iter_project_files(root):
        if not is_probably_text(project_file.path, project_file.size):
            continue
        files_checked += 1
        text = read_text_file(project_file.path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in SECRET_PATTERNS + HEURISTIC_PATTERNS:
                if pattern.search(line):
                    severity = "high"
                    if "Usage" in kind:
                        severity = "medium"
                    findings.append(
                        SecurityFinding(
                            path=project_file.relative_path,
                            line=line_number,
                            kind=kind,
                            severity=severity,
                            evidence=redact_secrets(line.strip())[:160],
                        )
                    )

    try:
        import sys
        bandit_result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", str(root), "-f", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if bandit_result.stdout:
            data = json.loads(bandit_result.stdout)
            for issue in data.get("results", []):
                rel_path = issue["filename"]
                if rel_path.startswith(str(root)):
                    rel_path = rel_path[len(str(root)):].lstrip("/\\")
                findings.append(
                    SecurityFinding(
                        path=rel_path,
                        line=issue["line_number"],
                        kind=f"Bandit: {issue['issue_text']}",
                        severity=issue["issue_severity"].lower(),
                        evidence=issue["code"].strip()[:160],
                    )
                )
    except Exception:
        pass

    status = "attention needed" if findings else "clear"
    notes = [
        "WinterSolve combines offline heuristics and static analysis (Bandit) "
        "to detect flaws.",
        "Potential secrets are redacted in reports.",
    ]
    if findings:
        notes.append("Rotate exposed credentials if any finding is a real secret.")

    return SecuritySummary(
        status=status,
        offline_by_default=True,
        files_checked=files_checked,
        findings=findings[:50],
        notes=notes,
    )


def redact_secrets(text: str) -> str:
    redacted = text
    for _, pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_replacement, redacted)
    return redacted


def _replacement(match: re.Match[str]) -> str:
    if len(match.groups()) >= 2:
        return f"{match.group(1)}=<redacted>"
    return "<redacted-secret>"
