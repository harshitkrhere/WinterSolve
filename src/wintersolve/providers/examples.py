"""Optional AI provider examples.

These are reference implementations, not a requirement: every WinterSolve
command works offline. Client libraries are imported lazily so the package
installs and runs without them; ``pip install "wintersolve[ai]"`` adds them.
Prompts must be redacted (see ``wintersolve.modules.security.redact_secrets``)
before they reach a provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from wintersolve.providers.base import AIProvider, ProviderConfig, ProviderResponse


@dataclass(frozen=True)
class OpenAIConfig(ProviderConfig):
    """Configuration for the OpenAI provider example."""

    api_key: str | None = None
    organization: str | None = None


class OpenAIProvider:
    """Small OpenAI provider example using an already-redacted prompt."""

    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config

    def complete(self, prompt: str) -> ProviderResponse:
        try:
            from openai import OpenAI  # noqa: PLC0415 - optional dependency
        except ImportError as error:
            raise RuntimeError(
                "OpenAI provider requires the optional 'openai' package. "
                "Install with: pip install 'wintersolve[ai]'"
            ) from error

        api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OpenAI API key not provided. Set OPENAI_API_KEY.")

        client = OpenAI(
            api_key=api_key,
            organization=self.config.organization,
            base_url=self.config.base_url,
        )
        response = client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return ProviderResponse(
            text=response.choices[0].message.content or "",
            model=self.config.model,
            provider="openai",
        )


@dataclass(frozen=True)
class AnthropicConfig(ProviderConfig):
    """Configuration for the Anthropic provider example."""

    api_key: str | None = None


class AnthropicProvider:
    """Small Anthropic provider example using an already-redacted prompt."""

    def __init__(self, config: AnthropicConfig) -> None:
        self.config = config

    def complete(self, prompt: str) -> ProviderResponse:
        try:
            from anthropic import Anthropic  # noqa: PLC0415 - optional dependency
        except ImportError as error:
            raise RuntimeError(
                "Anthropic provider requires the optional 'anthropic' package. "
                "Install with: pip install 'wintersolve[ai]'"
            ) from error

        api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Anthropic API key not provided. Set ANTHROPIC_API_KEY.")

        client = Anthropic(api_key=api_key, base_url=self.config.base_url)
        response = client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return ProviderResponse(
            text=response.content[0].text if response.content else "",
            model=self.config.model,
            provider="anthropic",
        )


def create_provider(provider_name: str, config: ProviderConfig) -> AIProvider:
    """Create one of the bundled provider examples by name."""
    if provider_name == "openai":
        if not isinstance(config, OpenAIConfig):
            raise TypeError("openai provider requires OpenAIConfig.")
        return OpenAIProvider(config)
    if provider_name == "anthropic":
        if not isinstance(config, AnthropicConfig):
            raise TypeError("anthropic provider requires AnthropicConfig.")
        return AnthropicProvider(config)
    raise ValueError(f"Unknown provider: {provider_name}. Available: openai, anthropic")
