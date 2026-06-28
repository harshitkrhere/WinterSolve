from __future__ import annotations

import json

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


def render_scan_report(result: ScanResult, output_format: str = "text") -> str:
    if output_format == "markdown":
        return _render_markdown(result)
    return _render_text(result)


def _render_text(result: ScanResult) -> str:
    lines = [
        "WinterSolve Repo Scan",
        "=" * 21,
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


def _render_markdown(result: ScanResult) -> str:
    sections = [
        _markdown_section("Languages", _format_pairs(result.languages)),
        _markdown_section("Detected Stack", result.frameworks),
        _markdown_section("Important Files", result.important_files),
        _markdown_section("Likely Source Paths", result.likely_source_paths),
        _markdown_section("Likely Test Paths", result.likely_test_paths),
        _markdown_section("Risks", result.risks),
        _markdown_section("Recommendations", result.recommendations),
    ]
    lines = [
        "# WinterSolve Repo Scan",
        "",
        f"- Path: `{result.path}`",
        f"- Files: {result.total_files}",
        f"- Directories: {result.total_directories}",
        "",
    ]
    return "\n\n".join(["\n".join(lines).rstrip(), *sections]).rstrip()


def _section(title: str, items: list[str]) -> str:
    lines = [f"{title}:"]
    if not items:
        lines.append("  - None detected")
    else:
        lines.extend(f"  - {item}" for item in items)
    return "\n".join(lines)


def _markdown_section(title: str, items: list[str]) -> str:
    lines = [f"## {title}"]
    if not items:
        lines.append("")
        lines.append("- None detected")
    else:
        lines.append("")
        lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)


def _format_pairs(pairs: list[tuple[str, int]]) -> list[str]:
    return [f"{name}: {count}" for name, count in pairs]


def render_explanation(result: FileExplanation) -> str:
    return "\n".join(
        [
            "WinterSolve File Explanation",
            "=" * 29,
            f"Path: {result.path}",
            f"Language: {result.language}",
            f"Lines: {result.line_count}",
            "",
            _section("Summary", result.summary),
            _section("Symbols and sections", result.symbols),
            _section("Imports and dependencies", result.imports),
            _section("Risks", result.risks),
        ]
    ).rstrip()


def render_debug_analysis(result: DebugAnalysis) -> str:
    return "\n".join(
        [
            "WinterSolve Debug Analysis",
            "=" * 27,
            f"Source: {result.source}",
            f"Likely language: {result.likely_language}",
            "",
            _section("Signals", result.signals),
            _section("Likely causes", result.likely_causes),
            _section("Next steps", result.next_steps),
        ]
    ).rstrip()


def render_docs_suggestions(result: DocsSuggestion, include_draft: bool = False) -> str:
    lines = [
        "WinterSolve Docs Assistant",
        "=" * 26,
        f"Path: {result.path}",
        "",
        _section("Missing README sections", result.missing_sections),
        _section("Suggestions", result.suggestions),
    ]
    if include_draft:
        lines.extend(["", "README Draft:", "-------------", result.readme_draft])
    return "\n".join(lines).rstrip()


def render_review_result(result: ReviewResult) -> str:
    return "\n".join(
        [
            "WinterSolve Review Assistant",
            "=" * 28,
            f"Path: {result.path}",
            f"Git detected: {'yes' if result.git_available else 'no'}",
            "",
            _section("Changed files", result.changed_files),
            _section("Risks", result.risks),
            _section("Checklist", result.checklist),
        ]
    ).rstrip()


def render_brain_report(result: BrainReport, output_format: str = "text") -> str:
    if output_format == "json":
        return json.dumps(result.to_dict(), indent=2, sort_keys=True)
    if output_format == "markdown":
        return _render_brain_markdown(result)
    return _render_brain_text(result)


def _render_brain_text(result: BrainReport) -> str:
    lines = [
        "WinterSolve Repo Brain",
        "=" * 22,
        f"Project: {result.identity.name}",
        f"Path: {result.identity.path}",
        f"Offline mode: {'yes' if result.identity.offline_mode else 'no'}",
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
    header = [
        "# WinterSolve Repo Brain",
        "",
        f"- Project: `{result.identity.name}`",
        f"- Path: `{result.identity.path}`",
        f"- Offline mode: {'yes' if result.identity.offline_mode else 'no'}",
    ]
    return "\n\n".join(["\n".join(header), *sections]).rstrip()


def _format_commands(commands: list[CommandCandidate]) -> list[str]:
    return [
        f"{command.name}: `{command.command}` ({command.source}, {command.confidence})"
        for command in commands
    ]


def _format_architecture(sections: list[ArchitectureSection]) -> list[str]:
    return [
        f"{section.path}: {section.purpose}; notable: {', '.join(section.notable_files[:4])}"
        for section in sections
    ]


def _format_security(security: SecuritySummary) -> list[str]:
    items = [
        f"Status: {security.status}",
        f"Offline by default: {'yes' if security.offline_by_default else 'no'}",
        f"Files checked: {security.files_checked}",
    ]
    items.extend(security.notes)
    items.extend(
        f"{finding.severity}: {finding.kind} in {finding.path}:{finding.line} -> {finding.evidence}"
        for finding in security.findings
    )
    return items
