from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from wintersolve.project import is_probably_text, read_text_file


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


LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".md": "Markdown",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".ps1": "PowerShell",
}


def explain_file(path: Path) -> FileExplanation:
    if not path.exists() or not path.is_file():
        return FileExplanation(
            path=path,
            exists=False,
            language="Unknown",
            line_count=0,
            summary=[],
            symbols=[],
            imports=[],
            risks=[f"File does not exist: {path}"],
        )

    size = path.stat().st_size
    if not is_probably_text(path, size):
        return FileExplanation(
            path=path,
            exists=True,
            language="Binary or large file",
            line_count=0,
            summary=["WinterSolve skipped content analysis for this file."],
            symbols=[],
            imports=[],
            risks=["File is too large or not recognized as text."],
        )

    content = read_text_file(path)
    lines = content.splitlines()
    language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "Text")
    symbols: list[str] = []
    imports: list[str] = []

    if path.suffix.lower() == ".py":
        symbols, imports = _analyze_python(content)
    else:
        symbols = _generic_symbols(lines)
        imports = _generic_imports(lines)

    summary = _build_summary(path, language, lines, symbols, imports)
    risks = _build_risks(lines, symbols, imports)

    return FileExplanation(
        path=path,
        exists=True,
        language=language,
        line_count=len(lines),
        summary=summary,
        symbols=symbols,
        imports=imports,
        risks=risks,
    )


def _analyze_python(content: str) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(content)
    except SyntaxError as error:
        return [], [f"Python syntax error near line {error.lineno}: {error.msg}"]

    symbols: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(f"function {node.name}")
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or "."
            imports.append(module)
    return sorted(set(symbols)), sorted(set(imports))


def _generic_symbols(lines: list[str]) -> list[str]:
    symbols: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            symbols.append(stripped[:80])
        elif stripped.startswith("function "):
            symbols.append(stripped[:80])
        elif stripped.startswith("class "):
            symbols.append(stripped[:80])
        elif stripped.startswith("export "):
            symbols.append(stripped[:80])
    return symbols[:20]


def _generic_imports(lines: list[str]) -> list[str]:
    imports: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("import ", "from ", "require(")):
            imports.append(stripped[:100])
    return imports[:20]


def _build_summary(
    path: Path,
    language: str,
    lines: list[str],
    symbols: list[str],
    imports: list[str],
) -> list[str]:
    summary = [
        f"This appears to be a {language} file named {path.name}.",
        f"It contains {len(lines)} lines.",
    ]
    if symbols:
        summary.append(f"WinterSolve found {len(symbols)} notable symbols or sections.")
    if imports:
        summary.append(f"WinterSolve found {len(imports)} imports or dependency references.")
    if not symbols and not imports:
        summary.append("No major symbols or imports were detected with offline analysis.")
    return summary


def _build_risks(lines: list[str], symbols: list[str], imports: list[str]) -> list[str]:
    risks: list[str] = []
    if len(lines) > 500:
        risks.append("Large file: consider splitting responsibilities if the file is hard to maintain.")
    if not symbols and len(lines) > 120:
        risks.append("Long file with no obvious symbols or sections detected.")
    if any("syntax error" in item.lower() for item in imports):
        risks.append("The file may contain a syntax error.")
    return risks or ["No obvious file-level risks were detected."]

