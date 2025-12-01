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

    def logic_expert(self) -> Agent:
        return Agent(
            role="Algorithm Logic Verifier",
            goal="Verify the correctness of the solution against the problem requirements.",
            backstory=dedent("""
                You are a strict Algorithm Judge. Your sole focus is correctness.
                You check if the logic holds for all edge cases, boundary conditions, and potential constraints.
                You are modeled after rigorous Online Judge systems (BOJ, Codeforces).
            """),
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def performance_specialist(self) -> Agent:
        return Agent(
            role="Performance & Complexity Analyst",
            goal="Analyze Time and Space complexity and suggest optimizations.",
            backstory=dedent("""
                You are an Optimization Guru. You care about Big-O notation.
                You despise inefficient loops and redundant calculations.
                You look for the most optimal data structures and algorithmic approaches.
            """),
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def code_quality_mentor(self) -> Agent:
        return Agent(
            role="Clean Code Mentor",
            goal="Ensure code readability, proper naming, and maintainability.",
            backstory=dedent("""
                You are a Senior Software Engineer who values clean, Pythonic (or language-idiomatic) code.
                You look for bad variable names, lack of modularity, and messy structures.
                You want the code to be readable by humans, not just computers.
            """),
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def review_task(self, agent: Agent, focus_area: str) -> Task:
        return Task(
            description=dedent(f"""
                Analyze the provided solution code for the given problem.
                
                [Problem Info]
                {self.problem_info}

                [Solution Code]
                {self.solution_code}

                Your focus is: {focus_area}
                Provide a detailed report on your findings strictly related to your role.
            """),
            expected_output=dedent(f"""
                A structured section focused on {focus_area}.
                Include specific examples from the code and actionable suggestions.
            """),
            agent=agent,
        )

    def report_aggregator_task(self, agent: Agent, context: list[Task]) -> Task:
        return Task(
            description=dedent(f"""
                Synthesize the findings from the Logic Verifier, Performance Analyst, and Code Mentor.
                Create a final, comprehensive Markdown report in {self.llm_config.response_language}.
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
            context=context,
        )

    def kickoff(self) -> str:
        # Agents
        logic_agent = self.logic_expert()
        perf_agent = self.performance_specialist()
        quality_agent = self.code_quality_mentor()

        # Tasks
        logic_task = self.review_task(logic_agent, "Correctness, Logic, and Edge Cases")
        perf_task = self.review_task(
            perf_agent, "Time/Space Complexity and Optimizations"
        )
        quality_task = self.review_task(
            quality_agent, "Readability, Naming, and Best Practices"
        )

        # Final Synthesis Task
        # 이전 태스크들의 결과(context)를 종합하여 최종 보고서를 작성합니다.
        final_task = self.report_aggregator_task(
            quality_agent, context=[logic_task, perf_task, quality_task]
        )

        crew = Crew(
            agents=[logic_agent, perf_agent, quality_agent],
            tasks=[logic_task, perf_task, quality_task, final_task],
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
