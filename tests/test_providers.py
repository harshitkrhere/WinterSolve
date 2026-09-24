"""Provider examples, tested against stand-in SDKs so no network or API key is needed."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from wintersolve.providers import (
    AnthropicConfig,
    AnthropicProvider,
    OpenAIConfig,
    OpenAIProvider,
    create_provider,
)


class FakeOpenAI:
    """Just enough of ``openai.OpenAI`` to answer one chat completion."""

    last_client_options: ClassVar[dict[str, Any]] = {}

    def __init__(self, **options: Any) -> None:
        FakeOpenAI.last_client_options = options
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_: Any) -> SimpleNamespace:
        message = SimpleNamespace(content="openai says hi")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeAnthropic:
    """Just enough of ``anthropic.Anthropic`` to answer one message."""

    def __init__(self, **_: Any) -> None:
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(text="anthropic says hi")])


@pytest.fixture
def fake_sdks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))


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

    @pytest.mark.parametrize(
        ("name", "config", "expected"),
        [
            ("anthropic", OpenAIConfig(name="t", model="m"), "requires AnthropicConfig"),
            ("openai", AnthropicConfig(name="t", model="m"), "requires OpenAIConfig"),
        ],
    )
    def test_config_type_is_checked(self, name: str, config: Any, expected: str) -> None:
        with pytest.raises(TypeError, match=expected):
            create_provider(name, config)


@pytest.mark.usefixtures("fake_sdks")
class TestCompletions:
    def test_openai_returns_the_reply_and_passes_the_key(self) -> None:
        provider = OpenAIProvider(OpenAIConfig(name="t", model="gpt-x", api_key="k"))

        response = provider.complete("hello")

        assert response.text == "openai says hi"
        assert response.provider == "openai"
        assert FakeOpenAI.last_client_options["api_key"] == "k"

    def test_anthropic_returns_the_reply(self) -> None:
        provider = AnthropicProvider(AnthropicConfig(name="t", model="claude-x", api_key="k"))

        response = provider.complete("hello")

        assert response.text == "anthropic says hi"
        assert response.model == "claude-x"

    def test_openai_requires_a_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            OpenAIProvider(OpenAIConfig(name="t", model="m")).complete("hi")

    def test_anthropic_requires_a_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider(AnthropicConfig(name="t", model="m")).complete("hi")


class TestMissingSdks:
    @pytest.mark.parametrize(
        ("module", "provider"),
        [
            ("openai", OpenAIProvider(OpenAIConfig(name="t", model="m", api_key="k"))),
            ("anthropic", AnthropicProvider(AnthropicConfig(name="t", model="m", api_key="k"))),
        ],
    )
    def test_missing_package_explains_the_extra(
        self, monkeypatch: pytest.MonkeyPatch, module: str, provider: Any
    ) -> None:
        monkeypatch.setitem(sys.modules, module, None)  # makes ``import`` fail

        with pytest.raises(RuntimeError, match=r"wintersolve\[ai\]"):
            provider.complete("hi")
