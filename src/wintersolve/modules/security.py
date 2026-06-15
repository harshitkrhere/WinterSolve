from __future__ import annotations

import re
from pathlib import Path

from wintersolve.models import SecurityFinding, SecuritySummary
from wintersolve.project import iter_project_files, is_probably_text, read_text_file


SECRET_PATTERNS = [
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("Generic assignment secret", re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?([^'\"\s]{12,})")),
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
            for kind, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        SecurityFinding(
                            path=project_file.relative_path,
                            line=line_number,
                            kind=kind,
                            severity="high",
                            evidence=redact_secrets(line.strip())[:160],
                        )
                    )

    status = "attention needed" if findings else "clear"
    notes = [
        "WinterSolve runs offline by default and does not call AI providers during analysis.",
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

