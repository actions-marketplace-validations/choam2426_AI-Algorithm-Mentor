from dataclasses import dataclass
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


@dataclass(frozen=True)
class ModelOptions:
    efficient: str
    performance: str


DEFAULT_MODEL_MAP: dict[LLMProvider, ModelOptions] = {
    LLMProvider.OPENAI: ModelOptions(
        efficient="gpt-5-nano",
        performance="gpt-5",
    ),
    LLMProvider.ANTHROPIC: ModelOptions(
        efficient="claude-haiku-4-5",
        performance="claude-sonnet-4-5",
    ),
    LLMProvider.GOOGLE: ModelOptions(
        efficient="gemini-2.5-flash",
        performance="gemini-2.5-pro",
    ),
}

API_KEY_ENV_MAP: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GOOGLE: "GEMINI_API_KEY",
}
