"""Explain a single file with offline static analysis.

Python gets a real syntax-tree walk and JSON is parsed. Other common languages
get line patterns that find top-level definitions and imports, plus the
header comment when the author left one. Languages without patterns get the
basics and a plain statement that deeper analysis is not available yet,
rather than a guess.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from wintersolve.modules.docs_assistant import markdown_headings
from wintersolve.project import (
    DATA_FORMAT_BY_EXTENSION,
    LANGUAGE_BY_EXTENSION,
    is_probably_text,
    read_text_file,
)

LARGE_FILE_LINES = 500
LONG_FILE_WITHOUT_STRUCTURE_LINES = 120
MAX_SYMBOLS = 20
MAX_IMPORTS = 30
MAX_NAMED_PACKAGES = 5
MAX_DESCRIPTION_CHARS = 160
HEADER_SEARCH_LINES = 60
MIN_DESCRIPTION_WORDS = 3  # "Module dependencies." labels a section; it does not describe a file.
MAX_OUTLINE_LEVEL = 3

STANDARD_LIBRARY = "standard library"
THIRD_PARTY = "third-party"
LOCAL = "this project"


@dataclass(frozen=True)
class FileExplanation:
    path: Path
    exists: bool
    language: str
    line_count: int
    summary: list[str]
    symbols: list[str]
    imports: list[str]
    risks: list[str]
    errors: list[str]


@dataclass(frozen=True)
class FileStructure:
    """What a language-specific analysis found in one file."""

    symbols: list[str]
    imports: list[str]
    symbol_noun: str = "definition"
    import_summary: str | None = None
    description: str | None = None
    errors: list[str] = field(default_factory=list)


def explain_file(path: Path) -> FileExplanation:
    """Describe what a file is, what it defines, and what it depends on."""
    if not path.is_file():
        return FileExplanation(
            path=path,
            exists=False,
            language="Unknown",
            line_count=0,
            summary=[],
            symbols=[],
            imports=[],
            risks=[f"File does not exist: {path}"],
            errors=[],
        )

    if not is_probably_text(path, path.stat().st_size):
        return FileExplanation(
            path=path,
            exists=True,
            language="Binary or large file",
            line_count=0,
            summary=["WinterSolve skipped content analysis for this file."],
            symbols=[],
            imports=[],
            risks=["File is too large or not recognized as text."],
            errors=[],
        )

    content = read_text_file(path)
    line_count = len(content.splitlines())
    language = _language_label(path)
    analyze = ANALYZERS.get(language)
    structure = analyze(content, path) if analyze else None

    return FileExplanation(
        path=path,
        exists=True,
        language=language,
        line_count=line_count,
        summary=_build_summary(path, language, line_count, structure),
        symbols=structure.symbols[:MAX_SYMBOLS] if structure else [],
        imports=structure.imports[:MAX_IMPORTS] if structure else [],
        risks=_build_risks(line_count, structure),
        errors=structure.errors if structure else [],
    )


def _language_label(path: Path) -> str:
    suffix = path.suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(suffix) or DATA_FORMAT_BY_EXTENSION.get(suffix) or "Text"


# ------------------------------------------------------------------- Python


def _analyze_python(content: str, path: Path) -> FileStructure:
    try:
        tree = ast.parse(content)
    except SyntaxError as error:
        message = f"Python syntax error near line {error.lineno}: {error.msg}"
        return FileStructure(symbols=[], imports=[], errors=[message])

    symbols: list[str] = []
    imports: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = sum(
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) for child in node.body
            )
            symbols.append(_with_count(f"class {node.name}", methods, "method"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(f"function {node.name}")
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.update(_relative_import_names(node))
        elif _is_main_guard(node):
            symbols.append("runnable as a script (__main__ guard)")

    own_package = _python_package_name(path)
    docstring = ast.get_docstring(tree)
    description = docstring.strip().splitlines()[0] if docstring else None
    return FileStructure(
        symbols=symbols,
        imports=sorted(imports),
        import_summary=_summarize_imports(
            imports, lambda module: _python_import_kind(module, own_package)
        ),
        description=description,
    )


def _relative_import_names(node: ast.ImportFrom) -> list[str]:
    """Keep the leading dots so ``from .ctx import x`` reads as ``.ctx``, not ``ctx``."""
    dots = "." * node.level
    if node.module:
        return [dots + node.module]
    return [dots + alias.name for alias in node.names]  # ``from . import helpers``


def _is_main_guard(node: ast.AST) -> bool:
    """Detect ``if __name__ == "__main__":`` without unparsing the whole file."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and any(isinstance(c, ast.Constant) and c.value == "__main__" for c in test.comparators)
    )


def _python_package_name(path: Path) -> str | None:
    """The top-level package a module belongs to, found by following ``__init__.py`` upwards."""
    package = None
    directory = path.parent
    while (directory / "__init__.py").is_file() and directory.parent != directory:
        package = directory.name
        directory = directory.parent
    return package


def _python_import_kind(module: str, own_package: str | None) -> tuple[str, str]:
    top_level = module.partition(".")[0]
    if module.startswith(".") or top_level == own_package:
        return LOCAL, module
    if top_level in sys.stdlib_module_names:
        return STANDARD_LIBRARY, top_level
    return THIRD_PARTY, top_level


# ----------------------------------------------------------------------- Go

GO_IMPORT_LINE = re.compile(r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"', re.MULTILINE)
GO_IMPORT_BLOCK = re.compile(r"^\s*import\s*\((.*?)\)", re.MULTILINE | re.DOTALL)
GO_QUOTED = re.compile(r'"([^"]+)"')
GO_METHOD = re.compile(r"func\s*\(\s*\w*\s*\*?\s*(?P<receiver>\w+)[^)]*\)\s*(?P<name>\w+)")
GO_FUNC = re.compile(r"func\s+(?P<name>\w+)")
GO_TYPE = re.compile(r"type\s+(?P<name>\w+)(?:\[[^\]]*\])?\s+(?P<kind>struct|interface)?")


def _analyze_go(content: str, _path: Path) -> FileStructure:
    """Types with their method counts, then functions: how Go code is usually read."""
    imports = set(GO_IMPORT_LINE.findall(content))
    for block in GO_IMPORT_BLOCK.findall(content):
        imports.update(GO_QUOTED.findall(block))

    declared: list[tuple[str, str]] = []
    methods: Counter[str] = Counter()
    for line in content.splitlines():
        if match := GO_METHOD.match(line):
            methods[match["receiver"]] += 1
        elif match := GO_FUNC.match(line):
            declared.append(("func", match["name"]))
        elif match := GO_TYPE.match(line):
            declared.append((match["kind"] or "type", match["name"]))

    symbols = []
    for kind, name in declared:
        count = methods.pop(name, 0) if kind != "func" else 0
        symbols.append(_with_count(f"{kind} {name}", count, "method"))
    symbols.extend(f"methods on {receiver} ({count})" for receiver, count in methods.items())

    return FileStructure(
        symbols=symbols,
        imports=sorted(imports),
        import_summary=_summarize_imports(imports, _go_import_kind),
        description=_header_comment(content),
    )


def _go_import_kind(path: str) -> tuple[str, str]:
    # Standard library paths have no dot in their first element ("fmt", "net/http").
    first = path.split("/", maxsplit=1)[0]
    return (THIRD_PARTY, path) if "." in first else (STANDARD_LIBRARY, path)


# --------------------------------------------------- pattern-based languages


@dataclass(frozen=True)
class LanguageRules:
    """Regular expressions that find imports and definitions in one language.

    Import patterns run over the whole file (imports can span lines); the
    first non-empty group of each match is the module. Symbol patterns run
    against each line from its first character, so indented (nested)
    definitions are skipped unless a pattern allows leading whitespace. A
    ``name`` group is required; an ``export`` group marks exported symbols and
    a ``kind`` group overrides the label.

    Lines starting with one of ``comment_prefixes`` are ignored, so a code
    example in a doc comment (``* const x = require("x")``) is not an import.
    """

    imports: tuple[re.Pattern[str], ...]
    symbols: tuple[tuple[str, re.Pattern[str]], ...]
    comment_prefixes: tuple[str, ...] = ()
    classify: Callable[[str], tuple[str, str]] | None = None
    clean_import: Callable[[str], str] = str.strip
    symbol_noun: str = "definition"


C_STYLE_COMMENTS = ("//", "/*", "*")
HASH_COMMENTS = ("#",)


def _scan_with_rules(content: str, rules: LanguageRules) -> FileStructure:
    code_lines = [
        line
        for line in content.splitlines()
        if not (rules.comment_prefixes and line.lstrip().startswith(rules.comment_prefixes))
    ]
    code = "\n".join(code_lines)
    imports = {
        rules.clean_import(next(group for group in match.groups() if group))
        for pattern in rules.imports
        for match in pattern.finditer(code)
    }
    symbols: list[str] = []
    for line in code_lines:
        for kind, pattern in rules.symbols:
            if match := pattern.match(line):
                groups = match.groupdict()
                label = f"{groups.get('kind') or kind} {groups['name']}"
                symbols.append(f"export {label}" if groups.get("export") else label)
                break
    return FileStructure(
        symbols=list(dict.fromkeys(symbols)),
        symbol_noun=rules.symbol_noun,
        imports=sorted(imports),
        import_summary=_summarize_imports(imports, rules.classify) if rules.classify else None,
        description=_header_comment(content),
    )


def _pattern_analyzer(rules: LanguageRules) -> Callable[[str, Path], FileStructure]:
    def analyze(content: str, _path: Path) -> FileStructure:
        return _scan_with_rules(content, rules)

    return analyze


# JavaScript and TypeScript -------------------------------------------------

JS_NAME = r"(?P<name>[A-Za-z_$][\w$]*)"
JS_EXPORT = r"(?P<export>export\s+(?:default\s+)?)?(?:declare\s+)?"
NODE_BUILTINS = frozenset(
    {
        "assert",
        "buffer",
        "child_process",
        "cluster",
        "crypto",
        "dns",
        "events",
        "fs",
        "http",
        "http2",
        "https",
        "net",
        "os",
        "path",
        "perf_hooks",
        "process",
        "querystring",
        "readline",
        "stream",
        "timers",
        "tls",
        "url",
        "util",
        "v8",
        "vm",
        "worker_threads",
        "zlib",
    }
)


def npm_package_name(specifier: str) -> str:
    """Installable name behind an import: ``lodash/fp`` -> ``lodash``, ``@a/b/c`` -> ``@a/b``."""
    parts = specifier.split("/")
    return "/".join(parts[:2]) if specifier.startswith("@") else parts[0]


def _javascript_import_kind(specifier: str) -> tuple[str, str]:
    if specifier.startswith((".", "/", "@/", "~/")):
        return LOCAL, specifier
    package = npm_package_name(specifier)
    if package.startswith("node:") or package in NODE_BUILTINS:
        return STANDARD_LIBRARY, package.removeprefix("node:")
    return THIRD_PARTY, package


JAVASCRIPT_RULES = LanguageRules(
    comment_prefixes=C_STYLE_COMMENTS,
    imports=(
        # ``import x from "y"`` and ``export * from "y"``, including multi-line imports.
        re.compile(r"""^\s*(?:import|export)\b[^'"`;]*?\bfrom\s*['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""^\s*import\s*['"]([^'"]+)['"]""", re.MULTILINE),  # side-effect import
        re.compile(r"""\b(?:require|import)\(\s*['"]([^'"]+)['"]\s*\)"""),
    ),
    symbols=(
        ("function", re.compile(JS_EXPORT + r"(?:async\s+)?function\*?\s*" + JS_NAME)),
        ("class", re.compile(JS_EXPORT + r"(?:abstract\s+)?class\s+" + JS_NAME)),
        (
            "function",
            re.compile(
                JS_EXPORT + r"(?:const|let|var)\s+" + JS_NAME + r"\s*(?::[^=]+)?=\s*(?:async\s+)?"
                r"(?:function\b|(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*(?::[^=]+?)?=>)"
            ),
        ),
        ("interface", re.compile(JS_EXPORT + r"interface\s+" + JS_NAME)),
        ("type", re.compile(JS_EXPORT + r"type\s+" + JS_NAME + r"\b[^=]*=")),
        ("enum", re.compile(JS_EXPORT + r"(?:const\s+)?enum\s+" + JS_NAME)),
        ("constant", re.compile(r"(?P<export>export\s+)(?:const|let|var)\s+" + JS_NAME)),
    ),
    classify=_javascript_import_kind,
)

# Rust ----------------------------------------------------------------------

RUST_VISIBILITY = r"(?:pub(?:\([^)]*\))?\s+)?"


def _rust_import_kind(path: str) -> tuple[str, str]:
    crate = re.split(r"::|\{", path, maxsplit=1)[0].strip()
    if crate in {"std", "core", "alloc"}:
        return STANDARD_LIBRARY, crate
    if crate in {"crate", "self", "super"}:
        return LOCAL, path
    return THIRD_PARTY, crate


def _clean_rust_use(path: str) -> str:
    """``std::{\\n    io,\\n    fs,\\n}`` -> ``std::{io, fs}``."""
    compact = " ".join(path.split())
    return compact.replace("{ ", "{").replace(", }", "}").replace(" }", "}")


RUST_RULES = LanguageRules(
    comment_prefixes=C_STYLE_COMMENTS,
    imports=(
        re.compile(r"^\s*" + RUST_VISIBILITY + r"use\s+([^;]+);", re.MULTILINE),
        re.compile(r"^\s*extern\s+crate\s+(\w+)", re.MULTILINE),
    ),
    symbols=(
        (
            "fn",
            re.compile(
                RUST_VISIBILITY + r"(?:(?:const|async|unsafe|extern\s+\"[^\"]*\")\s+)*"
                r"fn\s+(?P<name>\w+)"
            ),
        ),
        ("struct", re.compile(RUST_VISIBILITY + r"struct\s+(?P<name>\w+)")),
        ("enum", re.compile(RUST_VISIBILITY + r"enum\s+(?P<name>\w+)")),
        ("trait", re.compile(RUST_VISIBILITY + r"(?:unsafe\s+)?trait\s+(?P<name>\w+)")),
        ("type", re.compile(RUST_VISIBILITY + r"type\s+(?P<name>\w+)")),
        ("mod", re.compile(RUST_VISIBILITY + r"mod\s+(?P<name>\w+)")),
        ("impl", re.compile(r"impl(?:<[^>]*>)?\s+(?P<name>[\w:<>, ]+?)\s*(?:where\b.*)?\{?\s*$")),
    ),
    classify=_rust_import_kind,
    clean_import=_clean_rust_use,
)

# JVM and .NET --------------------------------------------------------------

JAVA_RULES = LanguageRules(
    comment_prefixes=C_STYLE_COMMENTS,
    imports=(re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+(?:\.\*)?)\s*;", re.MULTILINE),),
    symbols=(
        (
            "class",
            re.compile(
                r"(?:(?:public|protected|private|abstract|final|static|sealed|non-sealed)\s+)*"
                r"(?P<kind>class|interface|enum|record)\s+(?P<name>\w+)"
            ),
        ),
        (
            "method",
            re.compile(
                r"(?: {4}|\t)(?:@\w+(?:\([^)]*\))?\s+)*(?:public|protected)\s+"
                r"(?:(?:static|final|abstract|synchronized|default)\s+)*(?:<[^>]+>\s+)?"
                r"[\w.<>\[\], ?]+\s+(?P<name>\w+)\s*\("
            ),
        ),
    ),
)

KOTLIN_MODIFIERS = (
    r"(?:(?:public|private|internal|protected|open|abstract|final|data|sealed|enum|inner|"
    r"inline|value|annotation|override|suspend|operator|infix|tailrec|expect|actual)\s+)*"
)
KOTLIN_RULES = LanguageRules(
    comment_prefixes=C_STYLE_COMMENTS,
    imports=(re.compile(r"^\s*import\s+([\w.*]+)", re.MULTILINE),),
    symbols=(
        (
            "class",
            re.compile(KOTLIN_MODIFIERS + r"(?P<kind>class|interface|object)\s+(?P<name>\w+)"),
        ),
        (
            "fun",
            re.compile(
                KOTLIN_MODIFIERS + r"fun\s+(?:<[^>]*>\s*)?(?:[\w.<>?]+\.)?(?P<name>\w+)\s*\("
            ),
        ),
    ),
)

CSHARP_RULES = LanguageRules(
    comment_prefixes=C_STYLE_COMMENTS,
    imports=(re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE),),
    symbols=(
        ("namespace", re.compile(r"namespace\s+(?P<name>[\w.]+)")),
        (
            "class",
            re.compile(
                r"\s*(?:(?:public|internal|private|protected|abstract|sealed|static|partial|"
                r"readonly|ref|file|unsafe)\s+)*(?P<kind>class|interface|enum|record|struct)"
                r"\s+(?P<name>\w+)"
            ),
        ),
        (
            "method",
            re.compile(
                r"\s{4,8}(?:public|protected|internal)\s+(?:(?:static|virtual|override|abstract|"
                r"async|sealed|new|extern|unsafe|partial)\s+)*[\w.<>\[\],? ]+\s+(?P<name>\w+)"
                r"\s*(?:<[^>]*>)?\s*\("
            ),
        ),
    ),
)

# C and C++ -----------------------------------------------------------------

C_RULES = LanguageRules(
    comment_prefixes=C_STYLE_COMMENTS,
    imports=(re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]", re.MULTILINE),),
    symbols=(
        (
            "struct",
            re.compile(
                r"(?:typedef\s+)?(?P<kind>struct|class|enum(?:\s+class)?|union|namespace)\s+"
                r"(?P<name>\w+)\s*(?:final\s*)?(?::[^;{]*)?\{?\s*$"
            ),
        ),
        (
            "function",
            re.compile(
                r"(?!(?:return|else|if|for|while|switch|do|case|typedef|using|template)\b)"
                r"(?:[\w:*&<>,~]+\s+)+\**&?(?P<name>~?[A-Za-z_][\w:]*)\s*\([^;]*$"
            ),
        ),
    ),
)

# Scripting languages -------------------------------------------------------

RUBY_RULES = LanguageRules(
    comment_prefixes=HASH_COMMENTS,
    imports=(
        re.compile(
            r"""^\s*(?:require|require_relative|load)\s*\(?\s*['"]([^'"]+)['"]""", re.MULTILINE
        ),
    ),
    symbols=(
        ("class", re.compile(r"\s*(?P<kind>class|module)\s+(?P<name>[A-Z][\w:]*)")),
        ("method", re.compile(r"\s*def\s+(?P<name>(?:self\.)?[\w?!=\[\]]+)")),
    ),
)

PHP_RULES = LanguageRules(
    comment_prefixes=(*C_STYLE_COMMENTS, *HASH_COMMENTS),
    imports=(
        re.compile(r"^\s*use\s+([\w\\]+)(?:\s+as\s+\w+)?\s*;", re.MULTILINE),
        re.compile(r"""(?:require|include)(?:_once)?\s*\(?\s*['"]([^'"]+)['"]"""),
    ),
    symbols=(
        ("namespace", re.compile(r"namespace\s+(?P<name>[\w\\]+)")),
        (
            "class",
            re.compile(
                r"\s*(?:(?:abstract|final|readonly)\s+)*(?P<kind>class|interface|trait|enum)\s+"
                r"(?P<name>\w+)"
            ),
        ),
        (
            "function",
            re.compile(
                r"\s*(?:(?:public|protected|private|static|abstract|final)\s+)*function\s+&?"
                r"(?P<name>\w+)"
            ),
        ),
    ),
)

SHELL_RULES = LanguageRules(
    comment_prefixes=HASH_COMMENTS,
    imports=(re.compile(r"^\s*(?:source|\.)\s+([^\s;]+)", re.MULTILINE),),
    symbols=(
        ("function", re.compile(r"function\s+(?P<name>[\w:.-]+)")),
        ("function", re.compile(r"(?P<name>[\w:.-]+)\s*\(\)")),
    ),
)

POWERSHELL_RULES = LanguageRules(
    comment_prefixes=HASH_COMMENTS,
    imports=(
        re.compile(r"^\s*Import-Module\s+(?:-Name\s+)?['\"]?([\w.\\/-]+)", re.MULTILINE | re.I),
        re.compile(r"^\s*\.\s+['\"]?([^'\"\s]+\.ps1)", re.MULTILINE),
    ),
    symbols=(
        ("function", re.compile(r"function\s+(?P<name>[\w-]+)", re.I)),
        ("class", re.compile(r"class\s+(?P<name>\w+)", re.I)),
    ),
)

# --------------------------------------------------------- documents and data


def _analyze_document(content: str, _path: Path) -> FileStructure:
    """Markdown and reStructuredText: the outline, a few heading levels deep."""
    outline = [
        f"{'#' * level} {text}"
        for level, text in markdown_headings(content)
        if level <= MAX_OUTLINE_LEVEL
    ]
    return FileStructure(symbols=outline, imports=[], symbol_noun="section")


JSON_KEY = re.compile(r'^(\s*)"([^"]+)"\s*:', re.MULTILINE)


def _analyze_json(content: str, _path: Path) -> FileStructure:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        if "//" in content or "/*" in content:
            # JSON with comments (tsconfig.json, VS Code settings) is valid for its tools.
            return FileStructure(
                symbols=_least_indented_keys(content), imports=[], symbol_noun="top-level key"
            )
        message = f"JSON does not parse: {error.msg} (line {error.lineno})"
        return FileStructure(symbols=[], imports=[], errors=[message])

    if isinstance(data, dict):
        return FileStructure(
            symbols=[f"key {key}" for key in data], imports=[], symbol_noun="top-level key"
        )
    if isinstance(data, list):
        return FileStructure(
            symbols=[f"a list of {_count(len(data), 'item')}"], imports=[], symbol_noun="entry"
        )
    return FileStructure(symbols=[], imports=[])


def _least_indented_keys(content: str) -> list[str]:
    keys = JSON_KEY.findall(content)
    if not keys:
        return []
    top_level = min(len(indent) for indent, _ in keys)
    return [f"key {name}" for indent, name in keys if len(indent) == top_level]


YAML_RULES = LanguageRules(
    imports=(),
    symbols=(("key", re.compile(r"(?P<name>[\w.\-\"']+)\s*:(?:\s|$)")),),
    symbol_noun="top-level key",
)

TOML_TABLE = re.compile(r"\s*(?P<name>\[\[?[^\]]+\]\]?)")
TOML_KEY = re.compile(r"(?P<name>[\w.\-\"']+)\s*=")


def _analyze_toml(content: str, _path: Path) -> FileStructure:
    """Tables, plus any keys that come before the first table."""
    symbols: list[str] = []
    in_table = False
    for line in content.splitlines():
        if table := TOML_TABLE.match(line):
            in_table = True
            symbols.append(table["name"])
        elif not in_table and (key := TOML_KEY.match(line)):
            symbols.append(f"key {key['name']}")
    return FileStructure(
        symbols=symbols,
        imports=[],
        symbol_noun="table or top-level key",
        description=_header_comment(content),
    )


ANALYZERS: dict[str, Callable[[str, Path], FileStructure]] = {
    "Python": _analyze_python,
    "Go": _analyze_go,
    "JavaScript": _pattern_analyzer(JAVASCRIPT_RULES),
    "TypeScript": _pattern_analyzer(JAVASCRIPT_RULES),
    "Vue": _pattern_analyzer(JAVASCRIPT_RULES),
    "Svelte": _pattern_analyzer(JAVASCRIPT_RULES),
    "Rust": _pattern_analyzer(RUST_RULES),
    "Java": _pattern_analyzer(JAVA_RULES),
    "Kotlin": _pattern_analyzer(KOTLIN_RULES),
    "C#": _pattern_analyzer(CSHARP_RULES),
    "C": _pattern_analyzer(C_RULES),
    "C++": _pattern_analyzer(C_RULES),
    "C/C++": _pattern_analyzer(C_RULES),
    "Ruby": _pattern_analyzer(RUBY_RULES),
    "PHP": _pattern_analyzer(PHP_RULES),
    "Shell": _pattern_analyzer(SHELL_RULES),
    "PowerShell": _pattern_analyzer(POWERSHELL_RULES),
    "Markdown": _analyze_document,
    "reStructuredText": _analyze_document,
    "JSON": _analyze_json,
    "TOML": _analyze_toml,
    "YAML": _pattern_analyzer(YAML_RULES),
}

# ------------------------------------------------------------ header comments

# Comment blocks that are not a description of the file.
LICENSE_HEADER = re.compile(r"copyright|licen[cs]e|spdx|all rights reserved", re.IGNORECASE)
TOOL_DIRECTIVE = re.compile(
    r"^(?:eslint|@ts-|prettier|go:|\+build|nolint|noqa|pylint|type:|@flow|jshint|-\*-)",
    re.IGNORECASE,
)
FILE_DOC_TAG = re.compile(r"^@(?:file(?:overview)?|module|description)\b\s*")
CODE_LINES_THAT_ARE_NOT_COMMENTS = ("#include", "#define", "#if", "#pragma", "#import", "#region")


def _header_comment(content: str) -> str | None:
    """First sentence of the comment at the top of a file, skipping licence headers.

    Go package docs, JSDoc file headers, and Rust ``//!`` crate docs all live
    here, and they are the author's own summary of the file.
    """
    blocks: list[list[str]] = [[]]
    for raw_line in content.splitlines()[:HEADER_SEARCH_LINES]:
        line = raw_line.strip()
        if not line:
            blocks.append([])
            continue
        if line.startswith(("#!", "'use strict'", '"use strict"')):
            continue
        text = _comment_text(line)
        if text is None:
            break  # First line of code: the header is over.
        if text.startswith("@"):
            if not FILE_DOC_TAG.match(text):
                continue  # JSDoc tags such as @private or @param
            text = FILE_DOC_TAG.sub("", text)
        if text and not TOOL_DIRECTIVE.match(text):
            blocks[-1].append(text)

    for block in blocks:
        joined = " ".join(block)
        if len(joined.split()) >= MIN_DESCRIPTION_WORDS and not LICENSE_HEADER.search(joined):
            return _first_sentence(joined)
    return None


def _comment_text(line: str) -> str | None:
    """The text of a comment line, or ``None`` when the line is code."""
    if line.startswith(CODE_LINES_THAT_ARE_NOT_COMMENTS):
        return None
    for marker in ("///", "//!", "//", "/**", "/*", "*/", "#", "*"):
        if line.startswith(marker):
            return line.removeprefix(marker).removesuffix("*/").strip()
    return None


def _first_sentence(text: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    if len(sentence) > MAX_DESCRIPTION_CHARS:
        return sentence[: MAX_DESCRIPTION_CHARS - 3].rstrip() + "..."
    return sentence


# ------------------------------------------------------------------ summary


def _summarize_imports(
    imports: Iterable[str], classify: Callable[[str], tuple[str, str]]
) -> str | None:
    """One sentence that sorts imports into standard library, third-party, and local."""
    modules = sorted(imports)
    if not modules:
        return None
    counts: Counter[str] = Counter()
    third_party: list[str] = []
    for module in modules:
        kind, name = classify(module)
        counts[kind] += 1
        if kind == THIRD_PARTY and name not in third_party:
            third_party.append(name)

    parts = []
    if counts[STANDARD_LIBRARY]:
        parts.append(f"{counts[STANDARD_LIBRARY]} from the standard library")
    if counts[THIRD_PARTY]:
        named = ", ".join(third_party[:MAX_NAMED_PACKAGES])
        more = ", ..." if len(third_party) > MAX_NAMED_PACKAGES else ""
        parts.append(f"{counts[THIRD_PARTY]} from third-party packages ({named}{more})")
    if counts[LOCAL]:
        parts.append(f"{counts[LOCAL]} from {LOCAL}")
    return f"It imports {_count(len(modules), 'module')}: {', '.join(parts)}."


def _build_summary(
    path: Path, language: str, line_count: int, structure: FileStructure | None
) -> list[str]:
    summary = [f"{path.name} is a {language} file with {_count(line_count, 'line')}."]
    if structure is None:
        if language in LANGUAGE_BY_EXTENSION.values():
            summary.append(f"Definitions and imports are not detected for {language} files yet.")
        return summary

    if structure.description:
        source = "docstring" if language == "Python" else "header comment"
        summary.append(f"Its {source} says: {structure.description}")
    if structure.symbols:
        total = len(structure.symbols)
        listed = f"; the first {MAX_SYMBOLS} are listed" if total > MAX_SYMBOLS else ""
        summary.append(f"It has {_count(total, structure.symbol_noun)}{listed}.")
    if structure.import_summary:
        summary.append(structure.import_summary)
    elif structure.imports:
        summary.append(f"It imports {_count(len(structure.imports), 'module or file')}.")
    if not structure.symbols and not structure.imports and not structure.errors:
        summary.append("No definitions or imports were found.")
    return summary


def _build_risks(line_count: int, structure: FileStructure | None) -> list[str]:
    risks: list[str] = []
    if structure and structure.errors:
        risks.append("The file does not parse; fix the reported syntax error first.")
    if line_count > LARGE_FILE_LINES:
        risks.append(
            "Large file: consider splitting responsibilities if the file is hard to maintain."
        )
    if structure and not structure.symbols and line_count > LONG_FILE_WITHOUT_STRUCTURE_LINES:
        risks.append("Long file with no obvious definitions or sections detected.")
    return risks or ["No obvious file-level risks were detected."]


def _with_count(label: str, number: int, noun: str) -> str:
    """``class Flask (58 methods)``; the count is left off when it is zero."""
    return f"{label} ({_count(number, noun)})" if number else label


def _count(number: int, noun: str) -> str:
    """``1 method``, ``3 methods``, ``2 tables or top-level keys``."""
    if number == 1:
        return f"1 {noun}"
    words = noun.split(" or ", 1)
    plural = " or ".join(_plural(word) for word in words)
    return f"{number} {plural}"


def _plural(noun: str) -> str:
    head, _, last = noun.rpartition(" ")
    if last.endswith(("s", "x", "ch", "sh")):
        last += "es"
    elif last.endswith("y") and last[-2:-1] not in "aeiou":
        last = last[:-1] + "ies"
    else:
        last += "s"
    return f"{head} {last}".strip()
