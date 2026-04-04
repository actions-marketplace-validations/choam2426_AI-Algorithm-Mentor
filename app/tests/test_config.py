import pytest

from src.config import LLMConfig, get_llm_config
from src.consts import LLMProvider


class TestGetLlmConfig:
    """Tests for get_llm_config with monkeypatched env vars."""

    def test_valid_config(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("MODEL_NAME", "gpt-4o")
        monkeypatch.setenv("REVIEW_LANGUAGE", "english")

        config = get_llm_config()

        assert isinstance(config, LLMConfig)
        assert config.provider == LLMProvider.OPENAI
        assert config.model_name == "gpt-4o"
        assert config.response_language == "english"

    def test_default_review_language(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("MODEL_NAME", "claude-sonnet-4-20250514")
        monkeypatch.delenv("REVIEW_LANGUAGE", raising=False)

        config = get_llm_config()

        assert config.response_language == "korean"

    def test_missing_llm_provider_raises(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.setenv("MODEL_NAME", "gpt-4o")

        with pytest.raises(ValueError, match="LLM_PROVIDER"):
            get_llm_config()

    def test_invalid_llm_provider_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "invalid_provider")
        monkeypatch.setenv("MODEL_NAME", "some-model")

        with pytest.raises(ValueError, match="잘못된 LLM_PROVIDER"):
            get_llm_config()

    def test_missing_model_name_uses_default(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "google")
        monkeypatch.delenv("MODEL_NAME", raising=False)

        config = get_llm_config()
        assert config.model_name == "gemini-3.1-flash"

    @pytest.mark.parametrize(
        "provider_str, expected_enum",
        [
            ("openai", LLMProvider.OPENAI),
            ("anthropic", LLMProvider.ANTHROPIC),
            ("google", LLMProvider.GOOGLE),
        ],
    )
    def test_all_valid_providers(self, monkeypatch, provider_str, expected_enum):
        monkeypatch.setenv("LLM_PROVIDER", provider_str)
        monkeypatch.setenv("MODEL_NAME", "test-model")

        config = get_llm_config()
        assert config.provider == expected_enum
