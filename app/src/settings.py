import os

class Settings:
    def __init__(self):
        # GitHub 관련 설정
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.commit_sha = os.getenv("GITHUB_SHA")
        self.repository_name = os.getenv("GITHUB_REPOSITORY")
        
        # LLM Provider 설정
        llm_provider_env = os.getenv("LLM_PROVIDER")
        self.llm_provider = llm_provider_env.lower() if llm_provider_env else None
        self.llm_model = os.getenv("LLM_MODEL")
        if not self.llm_model and self.llm_provider:
            self.llm_model = self.get_default_model_for_provider(self.llm_provider)
        
        # API Keys
        self.api_key = self.get_required_api_key()


    def get_required_api_key(self):
        """LLM_PROVIDER에 따라 필요한 API 키를 반환"""
        if self.llm_provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.llm_provider == "google":
            return os.getenv("GOOGLE_API_KEY")
        elif self.llm_provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        else:
            return None

    def get_default_model_for_provider(self, provider):
        """Provider별 기본 모델을 반환"""
        defaults = {
            "openai": "gpt-4o",
            "google": "gemini-2.5-pro",
            "anthropic": "claude-opus-4-20250514"
        }
        return defaults.get(provider, "gpt-4o")

    def is_valid(self):
        """기본 설정이 유효한지 검증하고 에러 메시지를 출력"""
        errors = []
        
        # GitHub 설정 검증
        if not self.github_token:
            errors.append("GITHUB_TOKEN is required")
        if not self.commit_sha:
            errors.append("GITHUB_SHA is required")
        if not self.repository_name:
            errors.append("GITHUB_REPOSITORY is required")
        
        # LLM Provider 검증
        if not self.llm_provider:
            errors.append("LLM_PROVIDER is required")
        elif self.llm_provider not in ["openai", "google", "anthropic"]:
            errors.append(f"Invalid LLM_PROVIDER: {self.llm_provider}. Must be one of: openai, google, anthropic")
        
        # API 키 검증
        if self.api_key is None:
            if self.llm_provider == "openai":
                errors.append("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'")
            elif self.llm_provider == "google":
                errors.append("GOOGLE_API_KEY is required when LLM_PROVIDER is 'google'")
            elif self.llm_provider == "anthropic":
                errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'")
        
        # 에러 메시지 출력
        if errors:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
        
        return len(errors) == 0