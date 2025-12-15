import asyncio

import httpx
from src.config import LLMConfig, get_github_config, get_llm_config
from src.crew import run_algorithm_review
from src.github_service import get_commit_data, write_comment_in_commit
from src.logger import logger
from src.scrapers.factory import get_scraper
from src.utils import parse_problem_url


async def process_file(
    filename: str, content: str, llm_config: LLMConfig, client: httpx.AsyncClient
) -> str | None:
    """
    단일 파일을 처리하여 리뷰 결과를 반환합니다.
    URL 파싱 -> 문제 정보 스크래핑 -> AI 리뷰 수행
    """
    parsed = parse_problem_url(content)
    if not parsed:
        logger.info(f"Skipping {filename}: No supported problem URL found.")
        return None

    platform, problem_id = parsed
    logger.info(f"Detected {platform} problem {problem_id} in {filename}")

    try:
        scraper = get_scraper(platform, client)
        problem_data = await scraper.get_problem(problem_id)
    except Exception as e:
        logger.error(f"Error scraping problem info for {filename}: {e}")
        return None

    # CrewAI에게 전달할 문제 정보 포맷팅
    problem_info_str = f"""
    Title: {problem_data.title}
    Platform: {problem_data.platform}
    URL: {problem_data.url}
    
    [Description]
    {problem_data.description}
    
    [Input Description]
    {problem_data.input_desc}
    
    [Output Description]
    {problem_data.output_desc}
    """

    # 동기 함수인 CrewAI 실행을 비동기 환경에서 실행 (블로킹 방지)
    # CrewAI 내부적으로 API 호출 등을 하므로 시간이 걸림
    try:
        review = await asyncio.to_thread(
            run_algorithm_review,
            problem_info=problem_info_str,
            solution_code=content,
            llm_config=llm_config,
        )
        return f"## 🧐 Review for `{filename}`\n\n{review}"
    except Exception as e:
        logger.error(f"Error running review for {filename}: {e}")
        return None


async def main_async():
    try:
        github_config = get_github_config()
        llm_config = get_llm_config()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    logger.info(f"Processing commit: {github_config.commit_sha}")

    # 1. 커밋된 파일 가져오기
    try:
        commit_data = get_commit_data(github_config)
    except Exception as e:
        logger.error(f"Error fetching commit data: {e}")
        return

    if not commit_data:
        logger.info("No supported files found in this commit.")
        return

    reviews = []
    async with httpx.AsyncClient() as client:
        tasks = []
        for filename, content in commit_data.items():
            tasks.append(process_file(filename, content, llm_config, client))

        # 병렬 처리
        results = await asyncio.gather(*tasks)
        reviews = [r for r in results if r]

    # 2. 리뷰 결과 코멘트로 등록
    if reviews:
        final_comment = "\n\n---\n\n".join(reviews)
        try:
            write_comment_in_commit(github_config, final_comment)
            logger.info("Successfully posted reviews.")
        except Exception as e:
            logger.error(f"Error posting comment: {e}")
    else:
        logger.info("No reviews generated.")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
