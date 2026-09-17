from __future__ import annotations

import pytest

from wintersolve.providers import (
    AnthropicConfig,
    AnthropicProvider,
    OpenAIConfig,
    OpenAIProvider,
    create_provider,
)


class TestCreateProvider:
    def test_builds_bundled_providers(self) -> None:
        openai = create_provider("openai", OpenAIConfig(name="t", model="gpt-4o", api_key="k"))
        anthropic = create_provider(
            "anthropic", AnthropicConfig(name="t", model="claude-sonnet-4-5", api_key="k")
        )

        assert isinstance(openai, OpenAIProvider)
        assert isinstance(anthropic, AnthropicProvider)

    def test_unknown_provider_names_the_options(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider: nope"):
            create_provider("nope", OpenAIConfig(name="t", model="m"))

    def test_config_type_is_checked(self) -> None:
        with pytest.raises(TypeError, match="requires AnthropicConfig"):
            create_provider("anthropic", OpenAIConfig(name="t", model="m"))


class TestMissingCredentials:
    def test_openai_requires_a_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            OpenAIProvider(OpenAIConfig(name="t", model="m")).complete("hi")

    def test_anthropic_requires_a_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider(AnthropicConfig(name="t", model="m")).complete("hi")
