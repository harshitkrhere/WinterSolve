from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from wintersolve.project import read_text_file


@dataclass(frozen=True)
class DebugAnalysis:
    source: str
    likely_language: str
    signals: list[str]
    likely_causes: list[str]
    next_steps: list[str]


PATTERNS = [
    (
        re.compile(r"ModuleNotFoundError|No module named", re.I),
        "Python dependency or import path issue",
    ),
    (re.compile(r"SyntaxError", re.I), "Syntax error in source code"),
    (re.compile(r"TypeError", re.I), "Unexpected value type or invalid function usage"),
    (re.compile(r"KeyError", re.I), "Missing dictionary key or configuration value"),
    (re.compile(r"IndexError", re.I), "List or array index is out of range"),
    (re.compile(r"Permission denied|EACCES", re.I), "File permission issue"),
    (
        re.compile(r"ECONNREFUSED|connection refused", re.I),
        "Service or server is not reachable",
    ),
    (
        re.compile(r"\bENOTFOUND\b|getaddrinfo", re.I),
        "DNS, host, or network configuration issue",
    ),
    (re.compile(r"Cannot find module", re.I), "Node.js dependency or path issue"),
    (
        re.compile(r"command not found|not recognized", re.I),
        "Missing command or PATH configuration issue",
    ),
]


def analyze_error_text(text: str, source: str = "inline input") -> DebugAnalysis:
    signals: list[str] = []
    likely_causes: list[str] = []

    for pattern, cause in PATTERNS:
        if pattern.search(text):
            likely_causes.append(cause)

    file_lines = re.findall(r'File "([^"]+)", line (\d+)', text)
    if file_lines:
        for file_name, line_number in file_lines[:8]:
            signals.append(f"Python stack frame: {file_name}:{line_number}")

    js_frames = re.findall(r"\(?([A-Za-z]:?[^()\s]+):(\d+):(\d+)\)?", text)
    if js_frames:
        for file_name, line_number, column in js_frames[:8]:
            signals.append(
                f"JavaScript stack frame: {file_name}:{line_number}:{column}"
            )

    likely_language = _guess_language(text)
    next_steps = _build_next_steps(likely_causes, signals)

    return DebugAnalysis(
        source=source,
        likely_language=likely_language,
        signals=signals or ["No stack-frame signals were detected."],
        likely_causes=sorted(set(likely_causes))
        or ["No known error pattern matched. More context may be needed."],
        next_steps=next_steps,
    )


def analyze_error_file(path: Path) -> DebugAnalysis:
    if not path.exists() or not path.is_file():
        return DebugAnalysis(
            source=str(path),
            likely_language="Unknown",
            signals=[],
            likely_causes=[f"Error file does not exist: {path}"],
            next_steps=["Provide a valid log, stack trace, or error text file."],
        )
    return analyze_error_text(read_text_file(path), source=str(path))


def _guess_language(text: str) -> str:
    if "Traceback (most recent call last)" in text or "ModuleNotFoundError" in text:
        return "Python"
    if "Cannot find module" in text or "node:" in text or "npm ERR!" in text:
        return "Node.js"
    if "panic:" in text:
        return "Go"
    if "thread 'main' panicked" in text:
        return "Rust"
    return "Unknown"


def _build_next_steps(likely_causes: list[str], signals: list[str]) -> list[str]:
    steps = ["Re-run the failing command and capture the full error output."]
    joined = " ".join(likely_causes).lower()
    if "dependency" in joined:
        steps.append(
            "Check that dependencies are installed and the active environment is "
            "correct."
        )
    if "syntax" in joined:
        steps.append("Open the referenced file and inspect the reported line first.")
    if "path" in joined or "command" in joined:
        steps.append(
            "Verify the command exists and that the project setup instructions "
            "were followed."
        )
    if signals and "No stack-frame" not in signals[0]:
        steps.append(
            "Start with the first stack frame that points into your project code."
        )
    steps.append(
        "After applying a fix, add or run a small test that reproduces the failure."
    )
    return steps
