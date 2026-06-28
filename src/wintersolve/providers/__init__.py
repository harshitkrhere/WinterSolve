"""Optional AI provider extension points."""

from wintersolve.providers.base import AIProvider, ProviderConfig, ProviderResponse
from wintersolve.providers.examples import (
    AnthropicConfig,
    AnthropicProvider,
    OpenAIConfig,
    OpenAIProvider,
    create_provider,
)

__all__ = [
    "AIProvider",
    "ProviderConfig",
    "ProviderResponse",
    "OpenAIConfig",
    "OpenAIProvider",
    "AnthropicConfig",
    "AnthropicProvider",
    "create_provider",
]
