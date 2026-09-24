"""Make sense of an error message, log excerpt, or stack trace.

Pattern matching, not magic. Each rule pairs a recognisable error signature
with a likely cause in plain language and the advice that goes with it. When
the error names the thing that went wrong (a missing module, a busy port, an
unknown command), the advice names it too, so the next step can be copied and
run as-is.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from wintersolve.modules.explainer import npm_package_name
from wintersolve.project import read_text_file

MAX_FRAMES = 8


@dataclass(frozen=True)
class DebugAnalysis:
    source: str
    likely_language: str
    signals: list[str]
    likely_causes: list[str]
    next_steps: list[str]


@dataclass(frozen=True)
class ErrorRule:
    """A recognisable error signature, what it usually means, and what to do.

    ``specific_advice`` reads details out of the error (a module name, a port)
    and returns ready-to-run steps. When it finds nothing to work with, the
    general ``advice`` is used instead.
    """

    pattern: re.Pattern[str]
    cause: str
    advice: tuple[str, ...]
    specific_advice: Callable[[str], list[str]] | None = None

    def steps_for(self, text: str) -> list[str]:
        specific = self.specific_advice(text) if self.specific_advice else []
        return specific or list(self.advice)


# ----------------------------------------------------------- specific advice

ACTIVE_ENVIRONMENT_HINT = (
    "Install into the environment that runs the code: activate the virtual environment "
    "first, and use `python -m pip` rather than a bare `pip`."
)

# Import names that differ from the name you install. Only well-known,
# unambiguous cases; anything else is suggested under its import name.
PACKAGE_FOR_IMPORT = {
    "attr": "attrs",
    "Bio": "biopython",
    "bs4": "beautifulsoup4",
    "Crypto": "pycryptodome",
    "cv2": "opencv-python",
    "dateutil": "python-dateutil",
    "docx": "python-docx",
    "dotenv": "python-dotenv",
    "fitz": "PyMuPDF",
    "git": "GitPython",
    "jwt": "PyJWT",
    "magic": "python-magic",
    "multipart": "python-multipart",
    "MySQLdb": "mysqlclient",
    "nacl": "PyNaCl",
    "OpenSSL": "pyOpenSSL",
    "PIL": "Pillow",
    "pptx": "python-pptx",
    "serial": "pyserial",
    "skimage": "scikit-image",
    "sklearn": "scikit-learn",
    "slugify": "python-slugify",
    "win32api": "pywin32",
    "yaml": "PyYAML",
    "zmq": "pyzmq",
}

# Standard-library modules that go missing for reasons pip alone cannot fix.
STANDARD_LIBRARY_GAPS = {
    "distutils": (
        "`distutils` was removed from the standard library in Python 3.12. Install "
        "`setuptools`, which still provides it: `python -m pip install setuptools`."
    ),
    "tkinter": (
        "`tkinter` ships with Python, but some Linux distributions package it "
        "separately (for example `sudo apt install python3-tk`)."
    ),
}

PYTHON_MISSING_MODULE = re.compile(r"No module named '([\w.]+)'(?:; '([\w.]+)' is not a package)?")
NODE_MISSING_MODULE = re.compile(r"(?:Cannot find module|Can't resolve) '([^']+)'")
PORT_IN_USE = re.compile(r"(?:EADDRINUSE|address already in use)[^\n]*?:(\d{2,5})\b", re.I)
MISSING_COMMAND = re.compile(
    r"([\w.+-]+): command not found(?!:)"  # bash: foo: command not found
    r"|command not found: ([\w.+-]+)"  # zsh: command not found: foo
    r"|'([^']+)' is not recognized as"  # cmd.exe and PowerShell
)


def _python_module_advice(text: str) -> list[str]:
    match = PYTHON_MISSING_MODULE.search(text)
    if not match:
        return []
    module, not_a_package = match.groups()
    if not_a_package:
        return [
            f"A file or folder named `{not_a_package}` in your project is probably hiding the "
            f"real `{not_a_package}` package: rename it and delete any `__pycache__` next to it."
        ]

    top_level = module.partition(".")[0]
    if top_level != module:
        return [
            f"`{top_level}` imported, but `{module}` does not exist in the installed version: "
            f"check it with `python -m pip show {top_level}`. Namespace packages such as "
            "`google.*` ship each submodule as its own package."
        ]
    if module in STANDARD_LIBRARY_GAPS:
        return [STANDARD_LIBRARY_GAPS[module]]
    if module in PACKAGE_FOR_IMPORT:
        package = PACKAGE_FOR_IMPORT[module]
        return [
            f"`{module}` is provided by the `{package}` package: "
            f"`python -m pip install {package}`.",
            ACTIVE_ENVIRONMENT_HINT,
        ]
    return [
        f"If `{module}` is a third-party package, install it: `python -m pip install {module}`.",
        f"If `{module}` is part of this project, run the command from the project root, "
        "or install the project with `python -m pip install -e .`.",
        ACTIVE_ENVIRONMENT_HINT,
    ]


def _node_module_advice(text: str) -> list[str]:
    match = NODE_MISSING_MODULE.search(text)
    if not match:
        return []
    specifier = match.group(1)
    if specifier.startswith((".", "/", "~")) or re.match(r"[A-Za-z]:[\\/]", specifier):
        return [
            f"`{specifier}` is a file path, not a package: check it relative to the importing "
            "file, including the extension and letter case (Linux and macOS are case-sensitive)."
        ]
    package = npm_package_name(specifier)
    return [
        f"Install `{package}`: `npm install {package}` "
        f"(or `pnpm add {package}` / `yarn add {package}`).",
        "If it is already in package.json, reinstall dependencies so node_modules matches "
        "the lockfile.",
    ]


def _port_advice(text: str) -> list[str]:
    match = PORT_IN_USE.search(text)
    if not match:
        return []
    port = match.group(1)
    return [
        f"Find what is using port {port}: `lsof -i :{port}` on macOS/Linux or "
        f"`netstat -ano | findstr :{port}` on Windows. Stop it, or run on another port."
    ]


def _command_advice(text: str) -> list[str]:
    match = MISSING_COMMAND.search(text)
    if not match:
        return []
    command = next(group for group in match.groups() if group)
    return [
        f"`{command}` is not installed or not on PATH: check with `which {command}` "
        f"(macOS/Linux) or `where {command}` (Windows).",
        "Tools installed with pip also run as `python -m <tool>`, which works even when "
        "their scripts folder is not on PATH.",
    ]


# --------------------------------------------------------------------- rules


def _rule(
    pattern: str,
    cause: str,
    *advice: str,
    specific_advice: Callable[[str], list[str]] | None = None,
) -> ErrorRule:
    return ErrorRule(re.compile(pattern, re.IGNORECASE), cause, advice, specific_advice)


# Order is the order causes are listed in, so specific rules come before the
# general ones they overlap with (a JavaScript "Cannot read properties of
# undefined" is also a TypeError).
RULES: list[ErrorRule] = [
    _rule(
        r"ModuleNotFoundError|No module named",
        "Python dependency or import path issue",
        "Check that the package is installed in the environment that runs the code.",
        ACTIVE_ENVIRONMENT_HINT,
        specific_advice=_python_module_advice,
    ),
    _rule(
        r"\bImportError\b",
        "Import failed: circular import, missing symbol, or wrong version",
        "Check that the installed version provides the name being imported "
        "(`python -m pip show <package>`).",
        "If two of your modules import each other, move one import inside the function "
        "that uses it to break the cycle.",
    ),
    _rule(
        r"\bSyntaxError\b|IndentationError",
        "Syntax error in source code",
        "Open the reported file and line; the real mistake is often just before it "
        "(an unclosed bracket, quote, or block).",
    ),
    _rule(
        r"Cannot read propert(?:y|ies) of (?:undefined|null)|(?:undefined|null) is not an object",
        "A value was undefined or null when the code read a property from it",
        "Find where that value comes from (props, an API response, a lookup); "
        "it was missing when this line ran.",
        "Guard it where it is used, for example `items?.map(...)` or `items ?? []`, "
        "or wait until the data has loaded.",
    ),
    _rule(
        r"is not a function",
        "Called something that is not a function (a typo, a wrong import, or an undefined value)",
        "Log the value just before the call to see what it really is, and check default "
        "versus named imports (`import x` versus `import { x }`).",
    ),
    _rule(
        r"\bTypeError\b",
        "Unexpected value type or invalid function usage",
        "Check the types of the values on the reported line; `None` or `undefined` where "
        "an object was expected is the most common cause.",
    ),
    _rule(
        r"\bAttributeError\b",
        "Attribute or method does not exist on that object (often None)",
        "If the object is `None`, find where it should have been set: a function "
        "without a `return` returns `None`.",
    ),
    _rule(
        r"\bNameError\b|\bReferenceError\b",
        "Name used before definition or missing import",
        "Check the spelling, and that the name is defined or imported before this line runs.",
    ),
    _rule(
        r"\bKeyError\b",
        "Missing dictionary key or configuration value",
        "Print the keys that are present, or use `.get(key, default)` if the key is "
        "optional. For configuration, check the environment variable or file that "
        "should provide it.",
    ),
    _rule(
        r"\bIndexError\b",
        "List or array index is out of range",
        "Check the length before indexing; an empty list is the usual culprit.",
    ),
    _rule(
        r"\bValueError\b",
        "A value had the right type but unexpected content",
        "Print the value that was passed in and compare it with the expected format "
        "(a number, a date, one of a fixed set of choices).",
    ),
    _rule(
        r"RecursionError|Maximum call stack",
        "Unbounded recursion",
        "Look for a function that calls itself, or two that call each other, without a "
        "stopping condition; the repeating frames in the trace show the loop.",
    ),
    _rule(
        r"UnicodeDecodeError|UnicodeEncodeError",
        "Text encoding mismatch (usually not UTF-8)",
        'Pass the encoding explicitly, for example `open(path, encoding="utf-8")`, '
        "or find which input is not UTF-8.",
    ),
    _rule(
        r"JSONDecodeError|Unexpected token .* in JSON|is not valid JSON",
        "Malformed or empty JSON input",
        "Print the raw text before parsing it; an empty response or an HTML error page "
        "is the usual cause.",
    ),
    _rule(
        r"FileNotFoundError|\bENOENT\b|No such file or directory",
        "File or directory path does not exist",
        "Print the absolute path being opened and the current working directory: relative "
        "paths resolve from where the command runs, not from the source file.",
    ),
    _rule(
        r"Permission denied|\bEACCES\b|\bEPERM\b",
        "File permission issue",
        "Check the file's owner and permissions, and whether another program has it open "
        "(common on Windows). Avoid running as administrator or root to get around it.",
    ),
    _rule(
        r"\bEADDRINUSE\b|address already in use",
        "Port is already in use by another process",
        "Find the process using the port (`lsof -i :<port>` on macOS/Linux, "
        "`netstat -ano` on Windows) and stop it, or run on another port.",
        specific_advice=_port_advice,
    ),
    _rule(
        r"ECONNREFUSED|connection refused",
        "Service or server is not reachable",
        "Check that the service is running and listening on the host and port the code "
        "uses (a database or API started in another terminal or container).",
    ),
    _rule(
        r"\bENOTFOUND\b|getaddrinfo|Name or service not known",
        "DNS, host, or network configuration issue",
        "Check the hostname for typos, and that this machine can reach the network "
        "(VPN, proxy, or offline).",
    ),
    _rule(
        r"\bETIMEDOUT\b|TimeoutError|timed out",
        "Operation timed out waiting on a network or process",
        "Check that the service is up and responsive; if the work is genuinely slow, "
        "raise the timeout deliberately instead of retrying in a loop.",
    ),
    _rule(
        r"\bSSL\b|CERTIFICATE_VERIFY_FAILED",
        "TLS certificate or SSL configuration issue",
        "Check the system clock and the certificate bundle (behind a corporate proxy, "
        "point the tool at your organisation's CA file). Do not turn verification off.",
    ),
    _rule(
        r"Unauthorized|invalid api key|authentication failed",
        "Authentication failed: missing or invalid credentials",
        "Confirm the expected environment variables or config values are set and "
        "current; keys expire and get rotated.",
    ),
    _rule(
        r"\bForbidden\b|(?:HTTP/[\d.]+|status(?:[ _]code)?\s*[:=]?)\s*403\b|\[403\]",
        "Authorization failed: credentials lack permission",
        "The credentials were accepted but lack permission: check the token's scopes "
        "or the account's role.",
    ),
    _rule(
        r"Cannot find module|Module not found: (?:Error: )?Can't resolve",
        "Node.js dependency or path issue",
        "Run the project's install command (`npm install`, `pnpm install`, or `yarn`) "
        "so node_modules matches the lockfile.",
        specific_advice=_node_module_advice,
    ),
    _rule(
        r"ResolutionImpossible|version conflict|peer dep|ERESOLVE",
        "Dependency version conflict",
        "Read which two packages want incompatible versions, then upgrade or pin one of "
        "them. Forcing the install (`--force`, `--legacy-peer-deps`) hides the conflict.",
    ),
    _rule(
        r"command not found|not recognized as|No such command",
        "Missing command or PATH configuration issue",
        "Check that the tool is installed and that its folder is on PATH.",
        specific_advice=_command_advice,
    ),
    _rule(
        r"nil pointer dereference",
        "A nil pointer or interface was used (Go)",
        "Check which value on the reported line can be nil, and check `err` before using a result.",
    ),
    _rule(
        r"called `(?:Option|Result)::unwrap\(\)`",
        "unwrap() on a None or Err value (Rust)",
        "Handle the empty or error case with `match`, `if let`, or `?` instead of `unwrap()`.",
    ),
    _rule(
        r"NullPointerException",
        "A null reference was used (JVM)",
        "Find which reference on the reported line is null, and where it should have been set.",
    ),
    _rule(
        r"Segmentation fault|SIGSEGV",
        "Native crash: memory corruption in a compiled extension",
        "Reinstall the compiled package so it matches this Python or Node version, and "
        "check its issue tracker for the release you have.",
    ),
    _rule(
        r"MemoryError|OutOfMemory|Killed process|heap out of memory",
        "Process ran out of memory",
        "Process the input in smaller chunks or stream it. For Node, "
        "`--max-old-space-size` raises the limit when the data really is that big.",
    ),
    _rule(
        r"OperationalError|could not connect to server|ECONNRESET",
        "Database or backend connection failed",
        "Check the connection URL, that the database is running, and that migrations "
        "have been applied.",
    ),
]

# --------------------------------------------------------------- stack frames

PYTHON_FRAME = re.compile(r'File "([^"]+)", line (\d+)')
JS_FRAME = re.compile(r"\(?((?:[A-Za-z]:)?[^()\s:]+\.[cm]?[jt]sx?):(\d+):(\d+)\)?")
# Paths that belong to installed libraries or the runtime, not the user's code.
LIBRARY_PATH = re.compile(
    r"(?:site|dist)-packages/|node_modules/|/lib/python\d|/python\d+/lib/|^<|^node:",
    re.IGNORECASE,
)
# "TypeError: ..." or pytest's "E   KeyError: ..." at the start of a line.
ERROR_HEADLINE = re.compile(
    r"^(?:E\s+)?((?:[\w.]+\.)?(?:[A-Z]\w*)?(?:Error|Exception|Exit|Interrupt)\b.*)$",
    re.MULTILINE,
)

# Text that gives away the runtime, checked in order. Exception names that only
# Python uses count; TypeError and SyntaxError do not, since JavaScript has them.
LANGUAGE_SIGNATURES = [
    (
        "Python",
        re.compile(
            r"Traceback \(most recent call last\)|\b(?:ModuleNotFound|Import|Key|Attribute|"
            r"Index|Name|Value|Indentation|ZeroDivision|FileNotFound|Recursion|JSONDecode)Error\b"
        ),
    ),
    ("Node.js", re.compile(r"Cannot find module|node:|npm (?:ERR!|error)|listen EADDRINUSE")),
    ("Go", re.compile(r"panic:|goroutine ")),
    ("Rust", re.compile(r"thread '[^']*' panicked|error\[E\d+\]")),
    ("Java / JVM", re.compile(r"Exception in thread|\n\s+at [\w.$]+\(")),
    ("JavaScript", re.compile(r"\bReferenceError\b|Cannot read propert")),
]


def analyze_error_text(text: str, source: str = "inline input") -> DebugAnalysis:
    """Analyze raw error text and return signals, likely causes, and next steps."""
    matched = [rule for rule in RULES if rule.pattern.search(text)]
    python_frames = PYTHON_FRAME.findall(text)
    js_frames = JS_FRAME.findall(text)

    signals = [
        f"Python stack frame: {file_name}:{line_number}"
        for file_name, line_number in python_frames[:MAX_FRAMES]
    ]
    signals.extend(
        f"JavaScript stack frame: {file_name}:{line_number}:{column}"
        for file_name, line_number, column in js_frames[:MAX_FRAMES]
    )
    headline = _error_headline(text, python_traceback=bool(python_frames))
    if headline:
        signals.insert(0, f"Message: {headline}")

    return DebugAnalysis(
        source=source,
        likely_language=_guess_language(
            text, has_python_frames=bool(python_frames), has_js_frames=bool(js_frames)
        ),
        signals=signals or ["No stack-frame signals were detected."],
        likely_causes=[rule.cause for rule in matched]
        or ["No known error pattern matched. More context may be needed."],
        next_steps=_build_next_steps(text, matched, python_frames, js_frames),
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


def _error_headline(text: str, *, python_traceback: bool) -> str | None:
    """The line that names the error. Python prints it last; most runtimes print it first."""
    headlines = ERROR_HEADLINE.findall(text)
    if not headlines:
        return None
    return str(headlines[-1] if python_traceback else headlines[0]).strip()


def _guess_language(text: str, *, has_python_frames: bool, has_js_frames: bool) -> str:
    if has_python_frames:
        return "Python"
    for language, signature in LANGUAGE_SIGNATURES:
        if signature.search(text):
            return language
    return "JavaScript" if has_js_frames else "Unknown"


def _build_next_steps(
    text: str,
    matched: list[ErrorRule],
    python_frames: list[tuple[str, str]],
    js_frames: list[tuple[str, str, str]],
) -> list[str]:
    steps: list[str] = []
    if not matched:
        steps.append(
            "Re-run the failing command and capture the full error output; "
            "the last few lines usually name the error type."
        )

    frame_step = _starting_frame_step(python_frames, js_frames)
    if frame_step:
        steps.append(frame_step)
    for rule in matched:
        steps.extend(rule.steps_for(text))
    steps.append("After applying a fix, add or run a small test that reproduces the failure.")
    return list(dict.fromkeys(steps))  # Drop repeats, keep order.


def _starting_frame_step(
    python_frames: list[tuple[str, str]], js_frames: list[tuple[str, str, str]]
) -> str | None:
    """Point at the deepest stack frame in the user's own code.

    Python prints the innermost frame last; JavaScript prints it first.
    """
    own_python = [(path, line) for path, line in python_frames if not _is_library(path)]
    own_js = [(path, line) for path, line, _ in js_frames if not _is_library(path)]
    if own_python:
        path, line = own_python[-1]
    elif own_js:
        path, line = own_js[0]
    elif python_frames or js_frames:
        return (
            "Every stack frame is inside a library or the runtime; look at the values "
            "your code passed into that library."
        )
    else:
        return None
    return f"Start at {path}, line {line}: the deepest stack frame in your own code."


def _is_library(path: str) -> bool:
    return bool(LIBRARY_PATH.search(path.replace("\\", "/")))
