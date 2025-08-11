from __future__ import annotations

import os
from langchain_core.language_models.chat_models import BaseChatModel

from .consts import LLMProvider
from .config import LLMConfig
from .logger import logger


def create_chat_llm(config: LLMConfig, temperature: float = 0.0) -> BaseChatModel:
    """Create a LangChain chat LLM instance based on provider.

    Provider mapping:
    - OPENAI -> langchain_openai.ChatOpenAI
    - ANTHROPIC -> langchain_anthropic.ChatAnthropic
    - GOOGLE -> langchain_google_genai.ChatGoogleGenerativeAI
    """
    provider = config.provider
    model_name = config.model

    if provider is LLMProvider.OPENAI:
        # Prefer passing via environment to avoid constructor param mismatches
        os.environ.setdefault("OPENAI_API_KEY", config.api_key)
        from langchain_openai import ChatOpenAI

        logger.info(f"initialize OpenAI chat model: {model_name}")
        return ChatOpenAI(model=model_name, temperature=temperature)

    if provider is LLMProvider.ANTHROPIC:
        os.environ.setdefault("ANTHROPIC_API_KEY", config.api_key)
        from langchain_anthropic import ChatAnthropic

        logger.info(f"initialize Anthropic chat model: {model_name}")
        return ChatAnthropic(model=model_name, temperature=temperature)

    if provider is LLMProvider.GOOGLE:
        os.environ.setdefault("GOOGLE_API_KEY", config.api_key)
        from langchain_google_genai import ChatGoogleGenerativeAI

        logger.info(f"initialize Google Generative AI chat model: {model_name}")
        # max_output_tokens is optional; keep defaults reasonable
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

    raise ValueError(f"Unsupported LLM provider: {provider}")

