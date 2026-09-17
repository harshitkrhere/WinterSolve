"""Make sense of an error message, log excerpt, or stack trace.

Pattern matching, not magic: each rule maps a recognisable error signature to
a likely cause in plain language, and the next steps are built from the causes
that matched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from wintersolve.project import read_text_file

MAX_FRAMES = 8


@dataclass(frozen=True)
class DebugAnalysis:
    source: str
    likely_language: str
    signals: list[str]
    likely_causes: list[str]
    next_steps: list[str]


def _rule(pattern: str, cause: str) -> tuple[re.Pattern[str], str]:
    return re.compile(pattern, re.IGNORECASE), cause


# Each rule maps an error signature to a likely cause. Order only affects the
# order causes are listed in.
PATTERNS: list[tuple[re.Pattern[str], str]] = [
    _rule(r"ModuleNotFoundError|No module named", "Python dependency or import path issue"),
    _rule(r"\bImportError\b", "Import failed: circular import, missing symbol, or wrong version"),
    _rule(r"\bSyntaxError\b|IndentationError", "Syntax error in source code"),
    _rule(r"\bTypeError\b", "Unexpected value type or invalid function usage"),
    _rule(r"\bAttributeError\b", "Attribute or method does not exist on that object (often None)"),
    _rule(r"\bNameError\b", "Name used before definition or missing import"),
    _rule(r"\bKeyError\b", "Missing dictionary key or configuration value"),
    _rule(r"\bIndexError\b", "List or array index is out of range"),
    _rule(r"\bValueError\b", "A value had the right type but unexpected content"),
    _rule(r"RecursionError|Maximum call stack", "Unbounded recursion"),
    _rule(r"UnicodeDecodeError|UnicodeEncodeError", "Text encoding mismatch (usually not UTF-8)"),
    _rule(r"JSONDecodeError|Unexpected token .* in JSON", "Malformed or empty JSON input"),
    _rule(
        r"FileNotFoundError|\bENOENT\b|No such file or directory",
        "File or directory path does not exist",
    ),
    _rule(r"Permission denied|\bEACCES\b|\bEPERM\b", "File permission issue"),
    _rule(r"\bEADDRINUSE\b|address already in use", "Port is already in use by another process"),
    _rule(r"ECONNREFUSED|connection refused", "Service or server is not reachable"),
    _rule(
        r"\bENOTFOUND\b|getaddrinfo|Name or service not known",
        "DNS, host, or network configuration issue",
    ),
    _rule(
        r"\bETIMEDOUT\b|TimeoutError|timed out",
        "Operation timed out waiting on a network or process",
    ),
    _rule(r"\bSSL\b|CERTIFICATE_VERIFY_FAILED", "TLS certificate or SSL configuration issue"),
    _rule(
        r"Unauthorized|invalid api key|authentication failed",
        "Authentication failed: missing or invalid credentials",
    ),
    _rule(r"\b403\b|Forbidden", "Authorization failed: credentials lack permission"),
    _rule(
        r"Cannot find module|Module not found: Can't resolve", "Node.js dependency or path issue"
    ),
    _rule(
        r"ResolutionImpossible|version conflict|peer dep|ERESOLVE", "Dependency version conflict"
    ),
    _rule(
        r"command not found|not recognized as an internal|No such command",
        "Missing command or PATH configuration issue",
    ),
    _rule(r"Segmentation fault|SIGSEGV", "Native crash: memory corruption in a compiled extension"),
    _rule(
        r"MemoryError|OutOfMemory|Killed process|heap out of memory", "Process ran out of memory"
    ),
    _rule(
        r"OperationalError|could not connect to server|ECONNRESET",
        "Database or backend connection failed",
    ),
]

PYTHON_FRAME = re.compile(r'File "([^"]+)", line (\d+)')
JS_FRAME = re.compile(r"\(?((?:[A-Za-z]:)?[^()\s:]+\.[cm]?[jt]sx?):(\d+):(\d+)\)?")


def analyze_error_text(text: str, source: str = "inline input") -> DebugAnalysis:
    """Analyze raw error text and return signals, likely causes, and next steps."""
    likely_causes = [cause for pattern, cause in PATTERNS if pattern.search(text)]

    signals = [
        f"Python stack frame: {file_name}:{line_number}"
        for file_name, line_number in PYTHON_FRAME.findall(text)[:MAX_FRAMES]
    ]
    signals.extend(
        f"JavaScript stack frame: {file_name}:{line_number}:{column}"
        for file_name, line_number, column in JS_FRAME.findall(text)[:MAX_FRAMES]
    )

    return DebugAnalysis(
        source=source,
        likely_language=_guess_language(text),
        signals=signals or ["No stack-frame signals were detected."],
        likely_causes=likely_causes
        or ["No known error pattern matched. More context may be needed."],
        next_steps=_build_next_steps(likely_causes, has_frames=bool(signals)),
    )


def analyze_error_file(path: Path) -> DebugAnalysis:
    if not path.is_file():
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
    if "panic:" in text or "goroutine " in text:
        return "Go"
    if "thread 'main' panicked" in text or "error[E" in text:
        return "Rust"
    if "Exception in thread" in text or re.search(r"\n\s+at [\w.$]+\(", text):
        return "Java / JVM"
    return "Unknown"


def _build_next_steps(likely_causes: list[str], *, has_frames: bool) -> list[str]:
    steps = ["Re-run the failing command and capture the full error output."]
    joined = " ".join(likely_causes).lower()
    if "dependency" in joined or "import" in joined:
        steps.append("Check that dependencies are installed and the active environment is correct.")
    if "syntax" in joined:
        steps.append("Open the referenced file and inspect the reported line first.")
    if "path" in joined or "command" in joined:
        steps.append(
            "Verify the command exists and that the project setup instructions were followed."
        )
    if "credentials" in joined:
        steps.append(
            "Confirm the expected environment variables or config values are set and current."
        )
    if "port" in joined:
        steps.append("Find the process using the port (lsof -i / netstat -ano) or change the port.")
    if "reachable" in joined or "network" in joined or "connection" in joined:
        steps.append(
            "Check that the service is running and that host, port, and firewall settings match."
        )
    if has_frames:
        steps.append("Start with the first stack frame that points into your project code.")
    steps.append("After applying a fix, add or run a small test that reproduces the failure.")
    return steps
