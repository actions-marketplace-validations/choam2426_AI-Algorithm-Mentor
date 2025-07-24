"""
AI Algorithm Mentor - Intelligent Code Review System

A sophisticated, enterprise-grade code review system that analyzes algorithm solutions
from online judge platforms and provides intelligent feedback using state-of-the-art
language models.

Key Features:
- Multi-LLM support (OpenAI, Google, Anthropic)
- Comprehensive error handling and logging
- Type-safe configuration management
- GitHub Actions integration
- Multilingual review support
- Robust web crawling for problem extraction

Author: AI Algorithm Mentor Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "AI Algorithm Mentor Team"

# Core components
from .config import AppConfig, LLMProvider
from .exceptions import (
    AIAlgorithmMentorError,
    ConfigurationError,
    GitHubAPIError,
    LLMServiceError,
    CrawlerError,
    FileProcessingError,
)
from .logger import get_logger, LoggerManager
from .llm_service import create_llm_service, LLMResponse
from .github_service import GitHubService
from .crawler_service import CrawlerService, ProblemInfo

__all__ = [
    # Core classes
    "AppConfig",
    "GitHubService", 
    "CrawlerService",
    "ProblemInfo",
    "LLMResponse",
    
    # Enums
    "LLMProvider",
    
    # Exceptions
    "AIAlgorithmMentorError",
    "ConfigurationError", 
    "GitHubAPIError",
    "LLMServiceError",
    "CrawlerError",
    "FileProcessingError",
    
    # Utilities
    "get_logger",
    "LoggerManager",
    "create_llm_service",
    
    # Metadata
    "__version__",
    "__author__",
]