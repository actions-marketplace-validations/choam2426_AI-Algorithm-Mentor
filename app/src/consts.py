from enum import Enum

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


DEFAULT_MODEL_MAP: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-5",
    LLMProvider.ANTHROPIC: "claude-haiku-4-5",
    LLMProvider.GOOGLE: "gemini-2.5-pro",
}

API_KEY_ENV_MAP: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GOOGLE: "GEMINI_API_KEY",
}
