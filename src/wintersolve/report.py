"""Render analyzer results as plain text, Markdown, or JSON.

Renderers return strings and never print, so the same output can go to a
terminal, a file, or a CI log without changes. Text output is deliberately
plain (no colour codes) so it pastes cleanly into issues and pull requests.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from wintersolve.models import (
    ArchitectureSection,
    BrainReport,
    CommandCandidate,
    SecuritySummary,
)
from wintersolve.modules.debugger import DebugAnalysis
from wintersolve.modules.docs_assistant import DocsSuggestion
from wintersolve.modules.explainer import FileExplanation
from wintersolve.modules.reviewer import ReviewResult
from wintersolve.modules.scanner import ScanResult

MAX_NOTABLE_FILES_SHOWN = 4


# --------------------------------------------------------------------------- scan


def render_scan_report(result: ScanResult, output_format: str = "text") -> str:
    if output_format == "json":
        return _to_json(result.to_dict())
    if output_format == "markdown":
        return _render_scan_markdown(result)
    return _render_scan_text(result)


def _render_scan_text(result: ScanResult) -> str:
    lines = [
        _title("WinterSolve Repo Scan"),
        f"Path: {result.path}",
        f"Files: {result.total_files}",
        f"Directories: {result.total_directories}",
        "",
        _section("Languages", _format_pairs(result.languages)),
        _section("Detected stack", result.frameworks),
        _section("Important files", result.important_files),
        _section("Likely source paths", result.likely_source_paths),
        _section("Likely test paths", result.likely_test_paths),
        _section("Risks", result.risks),
        _section("Recommendations", result.recommendations),
    ]
    return "\n".join(lines).rstrip()


def _render_scan_markdown(result: ScanResult) -> str:
    header = [
        "# WinterSolve Repo Scan",
        "",
        f"- Path: `{result.path}`",
        f"- Files: {result.total_files}",
        f"- Directories: {result.total_directories}",
    ]
    sections = [
        _markdown_section("Languages", _format_pairs(result.languages)),
        _markdown_section("Detected Stack", result.frameworks),
        _markdown_section("Important Files", result.important_files),
        _markdown_section("Likely Source Paths", result.likely_source_paths),
        _markdown_section("Likely Test Paths", result.likely_test_paths),
        _markdown_section("Risks", result.risks),
        _markdown_section("Recommendations", result.recommendations),
    ]
    return "\n\n".join(["\n".join(header), *sections]).rstrip()


# -------------------------------------------------------------------------- brain


def render_brain_report(result: BrainReport, output_format: str = "text") -> str:
    if output_format == "json":
        return _to_json(result.to_dict())
    if output_format == "markdown":
        return _render_brain_markdown(result)
    return _render_brain_text(result)


def _render_brain_text(result: BrainReport) -> str:
    lines = [
        _title("WinterSolve Repo Brain"),
        f"Project: {result.identity.name}",
        f"Path: {result.identity.path}",
        f"Offline mode: {_yes_no(result.identity.offline_mode)}",
        "",
        _section("Languages", _format_pairs(result.languages)),
        _section("Detected stack", result.stack),
        _section("Source layout", result.source_paths),
        _section("Test layout", result.test_paths),
        _section("Documentation health", result.docs_health),
        _section("Detected commands", _format_commands(result.commands)),
        _section("Architecture map", _format_architecture(result.architecture)),
        _section("Security and privacy", _format_security(result.security)),
        _section("Risks", result.risks),
        _section("Recommendations", result.recommendations),
        _section("Next actions", result.next_actions),
    ]
    return "\n".join(lines).rstrip()


def _render_brain_markdown(result: BrainReport) -> str:
    header = [
        "# WinterSolve Repo Brain",
        "",
        f"- Project: `{result.identity.name}`",
        f"- Path: `{result.identity.path}`",
        f"- Offline mode: {_yes_no(result.identity.offline_mode)}",
    ]
    sections = [
        _markdown_section("Languages", _format_pairs(result.languages)),
        _markdown_section("Detected Stack", result.stack),
        _markdown_section("Source Layout", result.source_paths),
        _markdown_section("Test Layout", result.test_paths),
        _markdown_section("Documentation Health", result.docs_health),
        _markdown_section("Detected Commands", _format_commands(result.commands)),
        _markdown_section("Architecture Map", _format_architecture(result.architecture)),
        _markdown_section("Security and Privacy", _format_security(result.security)),
        _markdown_section("Risks", result.risks),
        _markdown_section("Recommendations", result.recommendations),
        _markdown_section("Next Actions", result.next_actions),
    ]
    return "\n\n".join(["\n".join(header), *sections]).rstrip()


# ------------------------------------------------------------------ other commands


def render_explanation(result: FileExplanation) -> str:
    lines = [
        _title("WinterSolve File Explanation"),
        f"Path: {result.path}",
        f"Language: {result.language}",
        f"Lines: {result.line_count}",
        "",
        _section("Summary", result.summary),
    ]
    if result.errors:
        lines.append(_section("Parse errors", result.errors))
    lines.extend(
        [
            _section("Symbols and sections", result.symbols),
            _section("Imports and dependencies", result.imports),
            _section("Risks", result.risks),
        ]
    )
    return "\n".join(lines).rstrip()


def render_debug_analysis(result: DebugAnalysis) -> str:
    lines = [
        _title("WinterSolve Debug Analysis"),
        f"Source: {result.source}",
        f"Likely language: {result.likely_language}",
        "",
        _section("Signals", result.signals),
        _section("Likely causes", result.likely_causes),
        _section("Next steps", result.next_steps),
    ]
    return "\n".join(lines).rstrip()


def render_docs_suggestions(result: DocsSuggestion, include_draft: bool = False) -> str:
    lines = [
        _title("WinterSolve Docs Assistant"),
        f"Path: {result.path}",
        "",
        _section("Missing README sections", result.missing_sections),
        _section("Suggestions", result.suggestions),
    ]
    if include_draft:
        lines.extend(["", "README Draft:", "-------------", result.readme_draft])
    return "\n".join(lines).rstrip()


def render_review_result(result: ReviewResult) -> str:
    lines = [
        _title("WinterSolve Review Assistant"),
        f"Path: {result.path}",
        f"Git detected: {_yes_no(result.git_available)}",
        "",
        _section("Changed files", result.changed_files),
        _section("Risks", result.risks),
        _section("Checklist", result.checklist),
    ]
    return "\n".join(lines).rstrip()


# ------------------------------------------------------------------------ helpers


def _title(text: str) -> str:
    return f"{text}\n{'=' * len(text)}"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _section(title: str, items: Sequence[str]) -> str:
    bullets = [f"  - {item}" for item in items] or ["  - None detected"]
    return "\n".join([f"{title}:", *bullets])


def _markdown_section(title: str, items: Sequence[str]) -> str:
    bullets = [f"- {item}" for item in items] or ["- None detected"]
    return "\n".join([f"## {title}", "", *bullets])


def _format_pairs(pairs: Sequence[tuple[str, int]]) -> list[str]:
    return [f"{name}: {count}" for name, count in pairs]


def _format_commands(commands: Sequence[CommandCandidate]) -> list[str]:
    return [
        f"{command.name}: `{command.command}` ({command.source}, {command.confidence})"
        for command in commands
    ]


def _format_architecture(sections: Sequence[ArchitectureSection]) -> list[str]:
    return [
        f"{section.path}: {section.purpose}; "
        f"notable: {', '.join(section.notable_files[:MAX_NOTABLE_FILES_SHOWN])}"
        for section in sections
    ]


def _format_security(security: SecuritySummary) -> list[str]:
    items = [
        f"Status: {security.status}",
        f"Offline by default: {_yes_no(security.offline_by_default)}",
        f"Files checked: {security.files_checked}",
        *security.notes,
    ]
    items.extend(
        f"{finding.severity}: {finding.kind} in {finding.path}:{finding.line} -> {finding.evidence}"
        for finding in security.findings
    )
    return items


def _to_json(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
