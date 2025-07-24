"""
Configuration management for AI Algorithm Mentor.

This module provides a centralized, type-safe configuration system
with validation, default values, and clear error messages.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from .exceptions import ConfigurationError
from .logger import get_logger

logger = get_logger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


# Review language is now handled as simple string with validation in prompt.py


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub-related configuration."""
    token: str
    repository: str
    commit_sha: str
    
    def __post_init__(self):
        """Validate GitHub configuration."""
        if not self.token:
            raise ConfigurationError("GitHub token is required")
        if not self.repository:
            raise ConfigurationError("GitHub repository is required")
        if not self.commit_sha:
            raise ConfigurationError("GitHub commit SHA is required")


@dataclass(frozen=True)
class LLMConfig:
    """LLM-related configuration."""
    provider: LLMProvider
    model: str
    api_key: str
    temperature: float = 0.1
    max_tokens: int = 2000
    
    def __post_init__(self):
        """Validate LLM configuration."""
        if not self.api_key:
            raise ConfigurationError(
                f"API key is required for {self.provider.value} provider"
            )
        if not (0.0 <= self.temperature <= 2.0):
            raise ConfigurationError(
                f"Temperature must be between 0.0 and 2.0, got {self.temperature}"
            )
        if self.max_tokens < 1:
            raise ConfigurationError(
                f"Max tokens must be positive, got {self.max_tokens}"
            )


@dataclass(frozen=True)
class CrawlerConfig:
    """Web crawler configuration."""
    headless: bool = True
    timeout: int = 15
    delay_between_requests: int = 2
    
    def __post_init__(self):
        """Validate crawler configuration."""
        if self.timeout < 1:
            raise ConfigurationError(
                f"Timeout must be positive, got {self.timeout}"
            )
        if self.delay_between_requests < 0:
            raise ConfigurationError(
                f"Delay must be non-negative, got {self.delay_between_requests}"
            )


@dataclass(frozen=True)
class AppConfig:
    """Complete application configuration."""
    github: GitHubConfig
    llm: LLMConfig
    crawler: CrawlerConfig
    review_language: str = "english"
    supported_file_extensions: tuple = (
        ".c", ".cpp", ".cc", ".cxx", ".py", ".java", ".js", ".go", ".rs"
    )
    
    @classmethod
    def from_environment(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        logger.info("🔧 Loading configuration from environment")
        
        try:
            # GitHub configuration
            github_config = GitHubConfig(
                token=cls._get_required_env("GITHUB_TOKEN"),
                repository=cls._get_required_env("GITHUB_REPOSITORY"),
                commit_sha=cls._get_required_env("GITHUB_SHA")
            )
            
            # LLM configuration
            provider_str = cls._get_required_env("LLM_PROVIDER").lower()
            try:
                provider = LLMProvider(provider_str)
            except ValueError:
                valid_providers = [p.value for p in LLMProvider]
                raise ConfigurationError(
                    f"Invalid LLM provider: {provider_str}. "
                    f"Must be one of: {', '.join(valid_providers)}"
                )
            
            model = os.getenv("LLM_MODEL") or cls._get_default_model(provider)
            api_key = cls._get_api_key_for_provider(provider)
            
            llm_config = LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                temperature=0.1,  # Fixed optimal value for code review
                max_tokens=2000   # Fixed optimal value for detailed reviews
            )
            
            # Crawler configuration with fixed optimal values
            crawler_config = CrawlerConfig(
                headless=True,    # Always headless in production
                timeout=15,       # Fixed timeout for stability
                delay_between_requests=2  # Fixed delay for rate limiting
            )
            
            # Review language (validation handled in prompt.py)
            review_language = os.getenv("REVIEW_LANGUAGE", "english").lower()
            
            logger.info(f"✅ Configuration loaded successfully for {provider.value} provider")
            
            return cls(
                github=github_config,
                llm=llm_config,
                crawler=crawler_config,
                review_language=review_language
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(f"Required environment variable {key} is not set")
        return value
    
    @staticmethod
    def _get_default_model(provider: LLMProvider) -> str:
        """Get default model for provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-4o",
            LLMProvider.GOOGLE: "gemini-2.0-flash-exp",
            LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022"
        }
        return defaults[provider]
    
    @staticmethod
    def _get_api_key_for_provider(provider: LLMProvider) -> str:
        """Get API key for the specified provider."""
        key_mapping = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY"
        }
        
        env_key = key_mapping[provider]
        api_key = os.getenv(env_key)
        
        if not api_key:
            raise ConfigurationError(
                f"API key {env_key} is required for {provider.value} provider"
            )
        
        return api_key
    
    def validate(self) -> List[str]:
        """Validate the entire configuration and return any errors."""
        errors = []
        
        try:
            # Validation is done in __post_init__ methods
            pass
        except ConfigurationError as e:
            errors.append(str(e))
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging."""
        return {
            "github": {
                "repository": self.github.repository,
                "commit_sha": self.github.commit_sha[:8] + "...",  # Truncate for privacy
                "token_present": bool(self.github.token)
            },
            "llm": {
                "provider": self.llm.provider.value,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "api_key_present": bool(self.llm.api_key)
            },
            "crawler": {
                "headless": self.crawler.headless,
                "timeout": self.crawler.timeout,
                "delay": self.crawler.delay_between_requests
            },
            "review_language": self.review_language,
            "supported_extensions": self.supported_file_extensions
        }
