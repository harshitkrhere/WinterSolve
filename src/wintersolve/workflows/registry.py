"""Registry of public workflows: the single list the CLI and docs draw from."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workflow:
    name: str
    summary: str
    offline: bool
    output_formats: list[str]


def get_workflows() -> list[Workflow]:
    """Every public ``wintersolve <workflow>`` command, in the order docs list them."""
    return [
        Workflow("brain", "Full project intelligence report", True, ["text", "markdown", "json"]),
        Workflow("scan", "Quick repository health check", True, ["text", "markdown", "json"]),
        Workflow("explain", "Offline explanation of one file", True, ["text"]),
        Workflow("debug", "Error, log, and stack trace analysis", True, ["text"]),
        Workflow("docs", "README and hygiene-file suggestions", True, ["text"]),
        Workflow("review", "Pre-review checklist for local changes", True, ["text"]),
    ]
