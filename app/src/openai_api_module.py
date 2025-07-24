"""
Legacy OpenAI API module.

This module is deprecated and kept only for backward compatibility.
Please use the new llm_service.py module instead.
"""

from typing import Dict, Any
import openai

from .prompt import get_prompt
from .logger import get_logger

logger = get_logger(__name__)


def get_code_review_by_openai(api_key: str, file_contents: Dict[str, str]) -> str:
    """
    Legacy function for OpenAI code review.
    
    DEPRECATED: Use llm_service.OpenAIService instead.
    """
    logger.warning("🚨 get_code_review_by_openai is deprecated. Please migrate to llm_service.OpenAIService")
    
    client = openai.OpenAI(api_key=api_key)
    prompt = get_prompt(file_contents)
    
    completion = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        top_p=1.0,
        frequency_penalty=0,
        presence_penalty=0,
        messages=prompt,
    )
    
    response = completion.choices[0].message.content
    return response if response else ""
