from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    base_url: str | None = None
    redaction_enabled: bool = True


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str
    provider: str


class AIProvider(Protocol):
    config: ProviderConfig

    def complete(self, prompt: str) -> ProviderResponse:
        """Return an AI completion for an already-redacted prompt."""

