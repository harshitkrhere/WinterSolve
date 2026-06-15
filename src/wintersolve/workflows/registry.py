from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workflow:
    name: str
    summary: str
    offline: bool
    output_formats: list[str]


def get_workflows() -> list[Workflow]:
    return [
        Workflow("scan", "Lightweight repository health scan", True, ["text", "markdown"]),
        Workflow("explain", "Offline file explanation", True, ["text"]),
        Workflow("debug", "Error and stack trace analysis", True, ["text"]),
        Workflow("docs", "Documentation health assistant", True, ["text"]),
        Workflow("review", "Local change review checklist", True, ["text"]),
        Workflow("brain", "Full project intelligence report", True, ["text", "markdown", "json"]),
    ]

