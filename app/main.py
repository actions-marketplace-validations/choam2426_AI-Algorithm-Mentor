import dotenv

dotenv.load_dotenv()
from src.consts import REVIEW_LANGUAGE
from src.github_service import get_current_commit_diff, write_comment_in_commit
from src.llm_service import create_llm
from src.online_judge_crawler import crawl_problems_from_text, format_problem_for_llm
from src.prompt import prompt


def main():
    review_target_file_contents = get_current_commit_diff()
    if not review_target_file_contents:
        print("No files to review.")
        return

    all_reviews = []
    
    for filepath, content in review_target_file_contents.items():
        print(f"Processing file: {filepath}")
        
        problem = crawl_problems_from_text(content)
        formatted_problem = ""
        
        if problem:
            formatted_problem = format_problem_for_llm(problem[0])
            print(f"Problem found and formatted for {filepath}")
        else:
            print(f"No problem URL found in {filepath}, proceeding with general review")

        data = {
            "problem_description": formatted_problem,
            "user_code": content,
            "review_language": REVIEW_LANGUAGE,
        }
        
        try:
            chain = prompt | create_llm()
            review_result = chain.invoke(data).content
            
            file_review = f"## 📁 파일: `{filepath}`\n\n{review_result}"
            all_reviews.append(file_review)
            print(f"Review generated for {filepath}")
            
        except Exception as e:
            error_msg = f"## 📁 파일: `{filepath}`\n\n❌ 리뷰 생성 중 오류가 발생했습니다: {str(e)}"
            all_reviews.append(error_msg)
            print(f"Error generating review for {filepath}: {e}")

    if all_reviews:
        final_comment = "\n\n---\n\n".join(all_reviews)
        final_comment += "\n\n---\n🤖 **AI Algorithm Mentor**에 의해 자동 생성된 리뷰입니다."
        
        try:
            success = write_comment_in_commit(final_comment)
            if success:
                print("✅ All reviews successfully posted to commit")
            else:
                print("❌ Failed to post reviews to commit")
        except Exception as e:
            print(f"❌ Error posting comment to commit: {e}")
    else:
        print("No reviews generated")


if __name__ == "__main__":
    main()
