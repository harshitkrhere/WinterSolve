"""Optional AI provider extension points. Nothing here is required for offline use."""

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
    "AnthropicConfig",
    "AnthropicProvider",
    "OpenAIConfig",
    "OpenAIProvider",
    "ProviderConfig",
    "ProviderResponse",
    "create_provider",
]
