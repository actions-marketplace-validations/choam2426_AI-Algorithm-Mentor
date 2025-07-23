from enum import Enum
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .consts import (
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)


class LLMProvider(Enum):
    """지원되는 LLM 제공자들"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


def create_llm(
    temperature: float = 0.1,
    max_tokens: Optional[int] = 2000,
    **kwargs: Any,
):
    """
    LLM_PROVIDER 상수 값에 따라 적절한 Langchain LLM 객체를 생성합니다.

    Args:
        provider (str): LLM 제공자 ("openai", "anthropic", "google")
        model_name (str, optional): 사용할 모델명
        temperature (float): 생성 온도 (0.0-1.0)
        max_tokens (int, optional): 최대 토큰 수
        api_key (str, optional): API 키 (없으면 환경변수에서 읽음)
        **kwargs: 추가 파라미터

    Returns:
        LangChain LLM 객체

    Raises:
        ValueError: 지원하지 않는 제공자이거나 필요한 설정이 누락된 경우
        ImportError: 필요한 패키지가 설치되지 않은 경우
    """

    provider = LLM_PROVIDER.lower().strip()

    try:
        if provider == LLMProvider.OPENAI.value:
            return _create_openai_llm(LLM_MODEL, temperature, max_tokens, **kwargs)

        elif provider == LLMProvider.ANTHROPIC.value:
            return _create_anthropic_llm(LLM_MODEL, temperature, max_tokens, **kwargs)

        elif provider == LLMProvider.GOOGLE.value:
            return _create_google_llm(LLM_MODEL, temperature, max_tokens, **kwargs)

        else:
            supported_providers = [p.value for p in LLMProvider]
            raise ValueError(
                f"지원하지 않는 제공자입니다: {provider}. 지원되는 제공자: {supported_providers}"
            )

    except ImportError as e:
        raise ImportError(
            f"{provider} 제공자를 사용하기 위해 필요한 패키지가 설치되지 않았습니다: {e}"
        )


def _create_openai_llm(
    model_name: Optional[str],
    temperature: float,
    max_tokens: Optional[int],
    **kwargs,
) -> ChatOpenAI:
    """OpenAI LLM 객체 생성"""
    params = {
        "model": model_name,
        "temperature": temperature,
        "api_key": OPENAI_API_KEY,
        **kwargs,
    }

    if max_tokens:
        params["max_tokens"] = max_tokens

    if not params["api_key"]:
        raise ValueError(
            "OpenAI API 키가 필요합니다. api_key 매개변수를 제공하거나 OPENAI_API_KEY 환경변수를 설정하세요."
        )

    return ChatOpenAI(**params)


def _create_anthropic_llm(
    model_name: Optional[str],
    temperature: float,
    max_tokens: Optional[int],
    **kwargs,
) -> ChatAnthropic:
    """Anthropic LLM 객체 생성"""

    params = {
        "model": model_name,
        "temperature": temperature,
        "anthropic_api_key": ANTHROPIC_API_KEY,
        **kwargs,
    }

    if max_tokens:
        params["max_tokens"] = max_tokens

    if not params["anthropic_api_key"]:
        raise ValueError(
            "Anthropic API 키가 필요합니다. api_key 매개변수를 제공하거나 ANTHROPIC_API_KEY 환경변수를 설정하세요."
        )

    return ChatAnthropic(**params)


def _create_google_llm(
    model_name: Optional[str],
    temperature: float,
    max_tokens: Optional[int],
    **kwargs,
) -> ChatGoogleGenerativeAI:
    """Google Generative AI LLM 객체 생성"""

    params = {
        "model": model_name,
        "temperature": temperature,
        "google_api_key": GOOGLE_API_KEY,
        **kwargs,
    }

    if max_tokens:
        params["max_output_tokens"] = max_tokens

    if not params["google_api_key"]:
        raise ValueError(
            "Google API 키가 필요합니다. api_key 매개변수를 제공하거나 GOOGLE_API_KEY 환경변수를 설정하세요."
        )

    return ChatGoogleGenerativeAI(**params)
