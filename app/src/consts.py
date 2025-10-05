from enum import Enum
from typing import List

SURPORT_FILE_EXTENSIONS: tuple = (
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".py",
    ".java",
    ".js",
    ".go",
    ".rs",
)


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


DEFAULT_MODEL_MAP: dict[LLMProvider, List[str]] = {
    LLMProvider.OPENAI: ["gpt-5", "gpt-5-nano"],
    LLMProvider.ANTHROPIC: ["claude-sonnet-4-5", "claude-sonnet-4-5"],
    LLMProvider.GOOGLE: ["gemini-2.5-pro", "gemini-2.5-flash"],
}

API_KEY_ENV_MAP: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GOOGLE: "GEMINI_API_KEY",
}
