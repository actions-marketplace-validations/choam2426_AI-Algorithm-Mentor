"""
Centralized logging configuration for AI Algorithm Mentor.

This module provides a sophisticated logging system with colored output,
structured formatting, and appropriate log levels for different components.
"""

import logging
import sys
from typing import Dict, Any
from enum import Enum


class LogLevel(Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for different log levels."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and emojis."""
        # Add emoji based on level
        emoji_map = {
            'DEBUG': '🐛',
            'INFO': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '💥'
        }
        
        # Get color and emoji
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        emoji = emoji_map.get(record.levelname, '📋')
        
        # Format timestamp
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        
        # Create formatted message
        formatted_msg = (
            f"{color}{emoji} [{timestamp}] "
            f"{record.levelname:<8} | {record.name:<20} | "
            f"{record.getMessage()}{reset}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted_msg += f"\n{self.formatException(record.exc_info)}"
        
        return formatted_msg


class LoggerManager:
    """Centralized logger management."""
    
    _loggers: Dict[str, logging.Logger] = {}
    _configured = False
    
    @classmethod
    def setup_logging(cls, level: str = "INFO") -> None:
        """Setup global logging configuration."""
        if cls._configured:
            return
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(console_handler)
        
        # Reduce noise from external libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger with the given name."""
        if not cls._configured:
            cls.setup_logging()
        
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        
        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return LoggerManager.get_logger(name)


class LogContext:
    """Context manager for structured logging with additional context."""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        self.logger = logger
        self.context = context
        self.original_format = None
    
    def __enter__(self):
        # Add context to all log messages
        context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"📋 Context: {context_str}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(f"💥 Context ended with exception: {exc_type.__name__}: {exc_val}")
        else:
            self.logger.info("✅ Context completed successfully")