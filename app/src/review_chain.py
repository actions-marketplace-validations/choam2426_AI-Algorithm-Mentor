import os

from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser

from .config import LLMConfig
from .consts import API_KEY_ENV_MAP, LLMProvider
from .prompt import get_prompt

PROVIDER_MAP: dict[LLMProvider, str] = {
    LLMProvider.GOOGLE: "google-genai",
    LLMProvider.OPENAI: "openai",
    LLMProvider.ANTHROPIC: "anthropic",
}


def run_algorithm_review(
    problem_info: str, solution_code: str, llm_config: LLMConfig
) -> str:
    """Run an algorithm review using a LangChain LCEL chain.

    Builds a prompt | llm | parser chain and invokes it to produce
    a Markdown review of the given solution code against the problem info.
    """
    mapped_provider = PROVIDER_MAP[llm_config.provider]

    # API 키를 명시적으로 전달 (GEMINI_API_KEY → google-genai의 api_key 등)
    api_key_env = API_KEY_ENV_MAP[llm_config.provider]
    api_key = os.getenv(api_key_env)

    llm = init_chat_model(
        model=llm_config.model_name,
        model_provider=mapped_provider,
        api_key=api_key,
    )
    prompt = get_prompt(problem_info, solution_code, llm_config.response_language)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({})
