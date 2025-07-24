"""
Custom exceptions for AI Algorithm Mentor.

This module defines all custom exceptions used throughout the application,
providing clear error hierarchies and meaningful error messages.
"""

from typing import Optional


class AIAlgorithmMentorError(Exception):
    """Base exception for all AI Algorithm Mentor errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConfigurationError(AIAlgorithmMentorError):
    """Raised when there are configuration or environment variable issues."""
    pass


class GitHubAPIError(AIAlgorithmMentorError):
    """Raised when GitHub API operations fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None):
        self.status_code = status_code
        super().__init__(message, details)
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.status_code:
            return f"HTTP {self.status_code}: {base_msg}"
        return base_msg


class LLMServiceError(AIAlgorithmMentorError):
    """Raised when LLM service operations fail."""
    pass


class CrawlerError(AIAlgorithmMentorError):
    """Raised when web crawling operations fail."""
    pass


class FileProcessingError(AIAlgorithmMentorError):
    """Raised when file processing operations fail."""
    pass