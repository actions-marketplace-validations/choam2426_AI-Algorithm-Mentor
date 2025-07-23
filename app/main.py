import dotenv

dotenv.load_dotenv()
from src.consts import REVIEW_LANGUAGE
from src.llm_service import create_llm
from src.online_judge_crawler import crawl_problems_from_text, format_problem_for_llm
from src.prompt import prompt


def main():
    # review_target_file_contents = get_current_commit_diff()
    # if not review_target_file_contents:
    #     print("No files to review.")
    #     return
    review_target_file_contents = {
        "example2.py": "# https://www.acmicpc.net/problem/1000\n a = input() \n b = input() \n print(a + b)\n",
    }
    for filepath, content in review_target_file_contents.items():
        problem = crawl_problems_from_text(content)
        if problem:
            formatted_problem = format_problem_for_llm(problem[0])
            print(f"Formatted Problem for LLM:\n{formatted_problem}")

        data = {
            "problem_description": formatted_problem,
            "user_code": content,
            "review_language": REVIEW_LANGUAGE,
        }
        chain = prompt | create_llm()

        print(chain.invoke(data).content)


if __name__ == "__main__":
    main()
