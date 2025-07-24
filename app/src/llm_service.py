"""
LLM Service Module for AI Algorithm Mentor.

This module provides a clean, type-safe interface to various LLM providers
with proper error handling, logging, and configuration management.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Union, Any, Optional
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig, LLMProvider
from .exceptions import LLMServiceError, ConfigurationError
from .logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from LLM service."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    
    def __str__(self) -> str:
        return self.content


class LLMServiceProtocol(Protocol):
    """Protocol defining the interface for LLM services."""
    
    def generate_review(self, problem_description: str, user_code: str, language: str) -> LLMResponse:
        """Generate a code review."""
        ...


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self._client: Optional[BaseChatModel] = None
    
    @property
    def client(self) -> BaseChatModel:
        """Lazy-loaded LLM client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    @abstractmethod
    def _create_client(self) -> BaseChatModel:
        """Create the LLM client."""
        pass
    
    def generate_review(self, problem_description: str, user_code: str, language: str) -> LLMResponse:
        """Generate a code review using the LLM."""
        try:
            logger.info(f"🤖 Generating review with {self.config.llm.provider.value} ({self.config.llm.model})")
            
            # Create messages
            system_message = self._create_system_message(language)
            user_message = self._create_user_message(problem_description, user_code)
            
            # Generate response
            response = self.client.invoke([system_message, user_message])
            
            logger.info("✅ Review generated successfully")
            
            return LLMResponse(
                content=response.content,
                provider=self.config.llm.provider.value,
                model=self.config.llm.model
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to generate review: {e}")
            raise LLMServiceError(f"Failed to generate review: {str(e)}")
    
    def _create_system_message(self, language: str) -> SystemMessage:
        """Create system message with review instructions."""
        from .prompt import get_system_prompt
        return SystemMessage(content=get_system_prompt(response_language=language))
    
    def _create_user_message(self, problem_description: str, user_code: str) -> HumanMessage:
        """Create user message with problem and code."""
        content = f"""**Problem Description:**
{problem_description if problem_description else "No specific problem description provided."}

**Code to Review:**
```
{user_code}
```"""
        return HumanMessage(content=content)


class OpenAIService(BaseLLMService):
    """OpenAI LLM service implementation."""
    
    def _create_client(self) -> ChatOpenAI:
        """Create OpenAI client."""
        try:
            params = {
                "model": self.config.llm.model,
                "temperature": self.config.llm.temperature,
                "max_tokens": self.config.llm.max_tokens,
                "api_key": self.config.llm.api_key,
            }
            
            logger.debug(f"🔧 Creating OpenAI client with model: {self.config.llm.model}")
            return ChatOpenAI(**params)
            
        except Exception as e:
            raise LLMServiceError(f"Failed to create OpenAI client: {str(e)}")


class AnthropicService(BaseLLMService):
    """Anthropic Claude LLM service implementation."""
    
    def _create_client(self) -> ChatAnthropic:
        """Create Anthropic client."""
        try:
            params = {
                "model": self.config.llm.model,
                "temperature": self.config.llm.temperature,
                "max_tokens": self.config.llm.max_tokens,
                "anthropic_api_key": self.config.llm.api_key,
            }
            
            logger.debug(f"🔧 Creating Anthropic client with model: {self.config.llm.model}")
            return ChatAnthropic(**params)
            
        except Exception as e:
            raise LLMServiceError(f"Failed to create Anthropic client: {str(e)}")


class GoogleService(BaseLLMService):
    """Google Generative AI LLM service implementation."""
    
    def _create_client(self) -> ChatGoogleGenerativeAI:
        """Create Google Generative AI client."""
        try:
            params = {
                "model": self.config.llm.model,
                "temperature": self.config.llm.temperature,
                "max_output_tokens": self.config.llm.max_tokens,  # Note: different parameter name
                "google_api_key": self.config.llm.api_key,
            }
            
            logger.debug(f"🔧 Creating Google client with model: {self.config.llm.model}")
            return ChatGoogleGenerativeAI(**params)
            
        except Exception as e:
            raise LLMServiceError(f"Failed to create Google client: {str(e)}")


class LLMServiceFactory:
    """Factory for creating LLM services."""
    
    _services = {
        LLMProvider.OPENAI: OpenAIService,
        LLMProvider.ANTHROPIC: AnthropicService,
        LLMProvider.GOOGLE: GoogleService,
    }
    
    @classmethod
    def create_service(cls, config: AppConfig) -> BaseLLMService:
        """Create an LLM service based on configuration."""
        service_class = cls._services.get(config.llm.provider)
        
        if not service_class:
            supported_providers = [p.value for p in LLMProvider]
            raise ConfigurationError(
                f"Unsupported LLM provider: {config.llm.provider.value}. "
                f"Supported providers: {', '.join(supported_providers)}"
            )
        
        logger.info(f"🏭 Creating {config.llm.provider.value} service")
        return service_class(config)


def create_llm_service(config: AppConfig) -> BaseLLMService:
    """Convenience function to create an LLM service."""
    return LLMServiceFactory.create_service(config)
