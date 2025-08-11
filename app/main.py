from src.config import get_github_config, get_llm_config
from src.github_service import fetch_changed_files_for_commit, post_commit_comment
from src.logger import logger
from src.online_judge import extract_problem_info_from_changed_files
from src.prompt import get_prompt
from src.llm_factory import create_chat_llm

def main():
    github_config = get_github_config()
    llm_config = get_llm_config()
    llm = create_chat_llm(llm_config)
    changed_files = fetch_changed_files_for_commit(github_config)
    logger.info(f"changed files collected: {len(changed_files)}")
    problem_infos = extract_problem_info_from_changed_files(changed_files)

    for path in problem_infos.keys():
        prompt = get_prompt(
            problem_info=problem_infos[path],
            solution_code=changed_files[path],
            output_language=llm_config.response_language,
        )
        chain = prompt | llm
        review = chain.invoke({})
        comment_text = review.content if hasattr(review, "content") else str(review)
        post_commit_comment(github_config, comment_text)
        

if __name__ == "__main__":
    main()