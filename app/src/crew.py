from textwrap import dedent

from crewai import LLM, Agent, Crew, Process, Task

from .config import LLMConfig
from .consts import LLMProvider


def get_crewai_llm(llm_config: LLMConfig) -> LLM:
    """
    config.py 설정을 기반으로 CrewAI의 LLM 객체(LiteLLM 기반)를 반환합니다.
    LiteLLM은 공급자(Provider)에 따라 모델명에 접두사가 필요할 수 있습니다.
    """
    model_name = llm_config.model_name

    # LiteLLM 모델 이름 규칙 적용 (provider/model_name)
    if llm_config.provider == LLMProvider.ANTHROPIC:
        if not model_name.startswith("anthropic/"):
            model_name = f"anthropic/{model_name}"
    elif llm_config.provider == LLMProvider.GOOGLE:
        if not model_name.startswith("gemini/"):
            model_name = f"gemini/{model_name}"
    elif llm_config.provider == LLMProvider.OPENAI:
        # OpenAI는 접두사 없이도 동작하지만, 명시적으로 openai/를 붙일 수 있습니다.
        # 여기서는 사용자가 환경 변수에 입력한 모델명을 우선합니다.
        pass

    # CrewAI의 LLM 클래스는 LiteLLM을 사용하여 모델을 호출합니다.
    # API 키는 환경 변수(OPENAI_API_KEY, ANTHROPIC_API_KEY 등)에서 자동으로 로드됩니다.
    return LLM(model=model_name)


class AlgorithmReviewCrew:
    def __init__(self, problem_info: str, solution_code: str, llm_config: LLMConfig):
        self.problem_info = problem_info
        self.solution_code = solution_code
        self.llm_config = llm_config
        self.llm = get_crewai_llm(llm_config)

    def algorithm_reviewer(self) -> Agent:
        return Agent(
            role="Algorithm Review Expert",
            goal="Provide comprehensive code review covering correctness, performance, and code quality.",
            backstory=dedent("""
                You are a Senior Algorithm Expert with deep knowledge in competitive programming and software engineering.
                You verify correctness like a strict Online Judge, analyze complexity like an optimization guru,
                and ensure clean, readable code like a seasoned mentor.
            """),
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def review_task(self, agent: Agent) -> Task:
        return Task(
            description=dedent(f"""
                Analyze the provided solution code for the given problem.
                
                [Problem Info]
                {self.problem_info}

                [Solution Code]
                {self.solution_code}

                Review the code from these perspectives:
                1. Correctness: Logic, edge cases, boundary conditions
                2. Performance: Time/Space complexity, optimizations
                3. Code Quality: Readability, naming, best practices

                Create a comprehensive Markdown report in {self.llm_config.response_language}.
                The report should be encouraging but technically rigorous.
            """),
            expected_output=dedent("""
                A final Markdown report containing:
                1. 📋 Problem Analysis Summary
                2. ✅ Correctness Verification
                3. ⚡ Performance Analysis
                4. 🎯 Improvement Suggestions (Refactoring, Optimization)
                5. 📚 Study Guide (Related concepts)
            """),
            agent=agent,
        )

    def kickoff(self) -> str:
        reviewer = self.algorithm_reviewer()
        task = self.review_task(reviewer)

        crew = Crew(
            agents=[reviewer],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        return str(result)


def run_algorithm_review(
    problem_info: str, solution_code: str, llm_config: LLMConfig
) -> str:
    crew_runner = AlgorithmReviewCrew(problem_info, solution_code, llm_config)
    return crew_runner.kickoff()
