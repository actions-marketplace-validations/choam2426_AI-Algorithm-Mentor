import os
from dataclasses import dataclass

from .consts import LLMProvider


@dataclass(frozen=True)
class GitHubConfig:
    commit_sha: str
    repository: str
    github_token: str


@dataclass(frozen=True)
class LLMConfig:
    provider: LLMProvider
    model_name: str
    response_language: str


def get_github_config() -> GitHubConfig:
    return GitHubConfig(
        commit_sha=os.getenv("GITHUB_SHA"),
        repository=os.getenv("GITHUB_REPOSITORY"),
        github_token=os.getenv("GITHUB_TOKEN"),
    )


def get_llm_config() -> LLMConfig:
    # LLM_PROVIDER 환경 변수 확인
    llm_provider_str = os.getenv("LLM_PROVIDER")
    if not llm_provider_str:
        raise ValueError("LLM_PROVIDER 환경 변수가 설정되지 않았습니다.")

    # LLM_PROVIDER 값 검증
    try:
        provider = LLMProvider(llm_provider_str)
    except ValueError:
        valid_providers = [p.value for p in LLMProvider]
        raise ValueError(
            f"잘못된 LLM_PROVIDER 값입니다: {llm_provider_str}. 유효한 값: {valid_providers}"
        )

    model_name = os.getenv("MODEL_NAME")
    if not model_name:
        raise ValueError("MODEL_NAME 환경 변수가 설정되지 않았습니다.")

    response_language = os.getenv("REVIEW_LANGUAGE", "korean")
    return LLMConfig(
        provider=provider,
        model_name=model_name,
        response_language=response_language,
    )
