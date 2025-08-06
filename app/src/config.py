from dataclasses import dataclass
from .consts import LLMProvider
import os

@dataclass(frozen=True)
class GitHubConfig:
    commit_sha: str
    repository: str
    github_token: str

@dataclass(frozen=True)
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str
    response_language: str

def get_github_config() -> GitHubConfig:
    return GitHubConfig(
        commit_sha=os.getenv("GITHUB_SHA"),
        repository=os.getenv("GITHUB_REPOSITORY"),
        github_token=os.getenv("GITHUB_TOKEN")
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
        raise ValueError(f"잘못된 LLM_PROVIDER 값입니다: {llm_provider_str}. 유효한 값: {valid_providers}")
    
    # 다른 필수 환경 변수들 확인
    model = os.getenv("LLM_MODEL")
    if not model:
        raise ValueError("LLM_MODEL 환경 변수가 설정되지 않았습니다.")
    
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    response_language = os.getenv("LLM_RESPONSE_LANGUAGE", "ko")
    
    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        response_language=response_language
    )
    