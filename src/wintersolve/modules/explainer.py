"""Explain a single file with offline static analysis.

Python files get a real ``ast`` walk (classes, functions, imports, docstring).
Everything else gets a lightweight line scan that still finds the obvious
structure: headings, ``function``/``class``/``export`` lines, and imports.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from wintersolve.project import (
    DATA_FORMAT_BY_EXTENSION,
    LANGUAGE_BY_EXTENSION,
    is_probably_text,
    read_text_file,
)

LARGE_FILE_LINES = 500
LONG_FILE_WITHOUT_STRUCTURE_LINES = 120
MAX_GENERIC_ITEMS = 20
SNIPPET_WIDTH = 80


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
    lines = content.splitlines()
    language = _language_label(path)

    if path.suffix.lower() in {".py", ".pyi"}:
        symbols, imports, errors, docstring = _analyze_python(content)
    else:
        symbols, imports, errors, docstring = (
            _generic_symbols(lines),
            _generic_imports(lines),
            [],
            None,
        )

    return FileExplanation(
        path=path,
        exists=True,
        language=language,
        line_count=len(lines),
        summary=_build_summary(path, language, len(lines), symbols, imports, docstring),
        symbols=symbols,
        imports=imports,
        risks=_build_risks(len(lines), symbols, errors),
        errors=errors,
    )


def _language_label(path: Path) -> str:
    suffix = path.suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(suffix) or DATA_FORMAT_BY_EXTENSION.get(suffix) or "Text"


def _analyze_python(content: str) -> tuple[list[str], list[str], list[str], str | None]:
    """Return (symbols, imports, errors, module docstring) for Python source."""
    try:
        tree = ast.parse(content)
    except SyntaxError as error:
        message = f"Python syntax error near line {error.lineno}: {error.msg}"
        return [], [], [message], None

    symbols: list[str] = []
    imports: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(f"function {node.name}")
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or ".")
        elif _is_main_guard(node):
            symbols.append("runnable as a script (__main__ guard)")

    docstring = ast.get_docstring(tree)
    first_line = docstring.strip().splitlines()[0] if docstring else None
    return symbols, sorted(imports), [], first_line


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


def _generic_symbols(lines: list[str]) -> list[str]:
    symbols: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(
            ("# ", "## ", "function ", "class ", "export ", "def ", "fn ", "func ")
        ):
            symbols.append(stripped[:SNIPPET_WIDTH])
    return symbols[:MAX_GENERIC_ITEMS]


def _generic_imports(lines: list[str]) -> list[str]:
    imports: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("import ", "from ", "require(", "use ", "#include ")):
            imports.append(stripped[: SNIPPET_WIDTH + 20])
    return imports[:MAX_GENERIC_ITEMS]


def _build_summary(
    path: Path,
    language: str,
    line_count: int,
    symbols: list[str],
    imports: list[str],
    docstring: str | None,
) -> list[str]:
    summary = [f"{path.name} is a {language} file with {line_count} lines."]
    if docstring:
        summary.append(f"Its docstring says: {docstring}")
    if symbols:
        summary.append(f"It defines {len(symbols)} notable symbols or sections.")
    if imports:
        summary.append(f"It references {len(imports)} imports or dependencies.")
    if not symbols and not imports:
        summary.append("No major symbols or imports were detected with offline analysis.")
    return summary


def _build_risks(line_count: int, symbols: list[str], errors: list[str]) -> list[str]:
    risks: list[str] = []
    if errors:
        risks.append("The file does not parse; fix the reported syntax error first.")
    if line_count > LARGE_FILE_LINES:
        risks.append(
            "Large file: consider splitting responsibilities if the file is hard to maintain."
        )
    if not symbols and line_count > LONG_FILE_WITHOUT_STRUCTURE_LINES:
        risks.append("Long file with no obvious symbols or sections detected.")
    return risks or ["No obvious file-level risks were detected."]
