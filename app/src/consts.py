from enum import Enum

SUPPORT_FILE_EXTENSIONS: tuple = (
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".py",
    ".java",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".cs",
    ".kt",
    ".kts",
    ".rb",
    ".swift",
)

COMMENT_PREFIX_MAP: dict[str, tuple[str, ...]] = {
    ".c": ("//", "/*"),
    ".cpp": ("//", "/*"),
    ".cc": ("//", "/*"),
    ".cxx": ("//", "/*"),
    ".py": ("#", '"""', "'''"),
    ".java": ("//", "/*"),
    ".js": ("//", "/*"),
    ".ts": ("//", "/*"),
    ".go": ("//", "/*"),
    ".rs": ("//", "/*"),
    ".cs": ("//", "/*"),
    ".kt": ("//", "/*"),
    ".kts": ("//", "/*"),
    ".rb": ("#", "=begin"),
    ".swift": ("//", "/*"),
}


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


API_KEY_ENV_MAP: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GOOGLE: "GEMINI_API_KEY",
}
