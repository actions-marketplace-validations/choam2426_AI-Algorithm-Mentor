from src.consts import REVIEW_LANGUAGE
from src.github_service import get_current_commit_diff
from src.online_judge_crawler import crawl_problems_from_text, format_problem_for_llm
from src.prompt import prompt


def main():
    review_target_file_contents = get_current_commit_diff()
    if not review_target_file_contents:
        print("No files to review.")
        return
    for filepath, content in review_target_file_contents.items():
        problem = crawl_problems_from_text(content)
        if problem:
            formatted_problem = format_problem_for_llm(problem[0])
            print(f"Formatted Problem for LLM:\n{formatted_problem}")
        prompt.format_prompt(
            problem_description=formatted_problem,
            user_code=content,
            review_language=REVIEW_LANGUAGE,
        )


if __name__ == "__main__":
    main()
