"""
AI Algorithm Mentor - Main Application

A sophisticated code review system that analyzes algorithm solutions from online judges
and provides intelligent feedback using state-of-the-art language models.

This application supports multiple LLM providers, comprehensive error handling,
and integrates seamlessly with GitHub Actions for automated code reviews.
"""

import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

import dotenv

# Load environment variables first
dotenv.load_dotenv()

from src.config import AppConfig
from src.exceptions import AIAlgorithmMentorError, ConfigurationError
from src.logger import LoggerManager, get_logger, LogContext
from src.github_service import GitHubService
from src.llm_service import create_llm_service
from src.crawler_service import CrawlerService

# Initialize logging
LoggerManager.setup_logging()
logger = get_logger(__name__)


@dataclass
class ReviewResult:
    """Result of a file review operation."""
    filepath: str
    success: bool
    review_content: Optional[str] = None
    error_message: Optional[str] = None


class AIAlgorithmMentor:
    """Main application class for AI Algorithm Mentor."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.github_service = GitHubService(config)
        self.llm_service = create_llm_service(config)
    
    def run(self) -> bool:
        """Run the complete review process."""
        logger.info("🚀 Starting AI Algorithm Mentor")
        
        try:
            with LogContext(logger, self.config.to_dict()):
                # Get files to review
                reviewable_files = self.github_service.get_reviewable_files()
                
                if not reviewable_files:
                    logger.info("📝 No files to review")
                    return True
                
                # Process each file
                review_results = self._process_files(reviewable_files)
                
                # Generate and post final comment
                success = self._post_final_review(review_results)
                
                if success:
                    logger.info("✅ AI Algorithm Mentor completed successfully")
                    return True
                else:
                    logger.error("❌ AI Algorithm Mentor completed with errors")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Critical error in AI Algorithm Mentor: {e}")
            return False
    
    def _process_files(self, files: Dict[str, str]) -> List[ReviewResult]:
        """Process all files and generate reviews."""
        logger.info(f"📋 Processing {len(files)} files")
        
        results = []
        
        for filepath, content in files.items():
            with LogContext(logger, {"file": filepath}):
                result = self._process_single_file(filepath, content)
                results.append(result)
        
        successful_reviews = sum(1 for r in results if r.success)
        logger.info(f"📊 Review summary: {successful_reviews}/{len(results)} successful")
        
        return results
    
    def _process_single_file(self, filepath: str, content: str) -> ReviewResult:
        """Process a single file and generate its review."""
        logger.info(f"📄 Processing file: {filepath}")
        
        try:
            # Extract problem information
            problem_description = self._extract_problem_info(content)
            
            # Generate review
            review = self.llm_service.generate_review(
                problem_description=problem_description,
                user_code=content,
                language=self.config.review_language
            )
            
            logger.info("✅ Review generated successfully")
            
            return ReviewResult(
                filepath=filepath,
                success=True,
                review_content=review.content
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to process file: {e}")
            
            return ReviewResult(
                filepath=filepath,
                success=False,
                error_message=str(e)
            )
    
    def _extract_problem_info(self, content: str) -> str:
        """Extract problem information from file content."""
        try:
            with CrawlerService(self.config) as crawler:
                problems = crawler.crawl_problems_from_text(content)
                
                if problems and problems[0].success:
                    logger.info("🎯 Problem information extracted successfully")
                    return problems[0].to_formatted_string()
                else:
                    logger.info("📝 No problem URL found, proceeding with general review")
                    return ""
                    
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract problem info: {e}")
            return ""
    
    def _post_final_review(self, results: List[ReviewResult]) -> bool:
        """Generate and post the final review comment."""
        logger.info("💬 Generating final review comment")
        
        try:
            comment_parts = []
            
            for result in results:
                if result.success and result.review_content:
                    file_section = f"## 📁 파일: `{result.filepath}`\n\n{result.review_content}"
                    comment_parts.append(file_section)
                else:
                    error_section = (
                        f"## 📁 파일: `{result.filepath}`\n\n"
                        f"❌ 리뷰 생성 중 오류가 발생했습니다: {result.error_message}"
                    )
                    comment_parts.append(error_section)
            
            if not comment_parts:
                logger.warning("⚠️ No review content generated")
                return False
            
            # Assemble final comment
            final_comment = "\n\n---\n\n".join(comment_parts)
            final_comment += (
                "\n\n---\n"
                f"🤖 **AI Algorithm Mentor** v1.0 - "
                f"Powered by {self.config.llm.provider.value.title()} ({self.config.llm.model})\n\n"
                f"🌍 Language: {self.config.review_language.value.title()} | "
                f"🕰️ Auto-generated review"
            )
            
            # Post comment
            success = self.github_service.post_review_comment(final_comment)
            
            if success:
                logger.info("✅ Final review posted successfully")
            else:
                logger.error("❌ Failed to post final review")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error posting final review: {e}")
            return False


def main() -> int:
    """Main entry point for AI Algorithm Mentor."""
    try:
        # Load configuration
        config = AppConfig.from_environment()
        
        # Create and run application
        app = AIAlgorithmMentor(config)
        success = app.run()
        
        return 0 if success else 1
        
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    
    except AIAlgorithmMentorError as e:
        logger.error(f"❌ Application error: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
