"""The minimal contract an AI provider must satisfy.

Providers receive an already-redacted prompt and return text. Keeping the
interface this small means new providers (local models included) are a few
dozen lines, and workflows never depend on a vendor SDK directly.
"""

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
    def complete(self, prompt: str) -> ProviderResponse:
        """Return a completion for an already-redacted prompt."""
