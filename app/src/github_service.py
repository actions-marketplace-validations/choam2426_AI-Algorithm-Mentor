"""
GitHub integration service for AI Algorithm Mentor.

This module provides robust GitHub API integration with proper error handling,
type safety, and comprehensive logging for all GitHub operations.
"""

import json
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import AppConfig
from .exceptions import GitHubAPIError, FileProcessingError
from .logger import get_logger, LogContext

logger = get_logger(__name__)


@dataclass(frozen=True)
class FileChange:
    """Represents a file change in a Git commit."""
    filepath: Path
    status: str  # A(dded), M(odified), D(eleted), R(enamed)
    content: Optional[str] = None
    
    @property
    def is_source_file(self) -> bool:
        """Check if this is a source code file we should review."""
        supported_extensions = (
            ".c", ".cpp", ".cc", ".cxx", ".py", ".java", ".js", ".go", ".rs"
        )
        return self.filepath.suffix.lower() in supported_extensions
    
    @property
    def should_review(self) -> bool:
        """Check if this file should be reviewed."""
        return self.status != "D" and self.is_source_file and self.content is not None


class GitService:
    """Service for Git-related operations."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def get_commit_changes(self) -> List[FileChange]:
        """Get all file changes from the current commit."""
        with LogContext(logger, {"commit_sha": self.config.github.commit_sha[:8]}):
            try:
                logger.info("🔍 Analyzing commit changes")
                
                # Get changed files
                git_command = ["git", "diff", "--name-status", "HEAD~1", "HEAD"]
                result = subprocess.run(
                    git_command, capture_output=True, text=True, check=True, timeout=30
                )
                
                if not result.stdout.strip():
                    logger.info("📝 No file changes detected")
                    return []
                
                changes = self._parse_git_output(result.stdout)
                source_changes = [c for c in changes if c.is_source_file]
                
                logger.info(
                    f"✅ Found {len(changes)} total changes, "
                    f"{len(source_changes)} source files for review"
                )
                
                return changes
                
            except subprocess.TimeoutExpired:
                raise FileProcessingError("Git command timed out")
            except subprocess.CalledProcessError as e:
                raise FileProcessingError(f"Git command failed: {e.stderr}")
            except Exception as e:
                raise FileProcessingError(f"Failed to get commit changes: {str(e)}")
    
    def _parse_git_output(self, output: str) -> List[FileChange]:
        """Parse git diff output into FileChange objects."""
        changes = []
        
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            
            status, filepath = parts[0], parts[1]
            path_obj = Path(filepath)
            content = None
            
            # Read file content if it's not deleted
            if status != "D":
                try:
                    with open(path_obj, "r", encoding="utf-8") as f:
                        content = f.read()
                except FileNotFoundError:
                    logger.warning(f"⚠️ File not found: {filepath}")
                    continue
                except UnicodeDecodeError:
                    logger.warning(f"⚠️ Cannot decode file: {filepath}")
                    continue
                except Exception as e:
                    logger.warning(f"⚠️ Error reading {filepath}: {e}")
                    continue
            
            changes.append(FileChange(
                filepath=path_obj,
                status=status,
                content=content
            ))
        
        return changes


class GitHubAPIService:
    """Service for GitHub API operations."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {config.github.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "AI-Algorithm-Mentor/1.0",
        }
    
    def post_commit_comment(self, comment: str) -> bool:
        """Post a comment to the specified commit."""
        url = (
            f"{self.base_url}/repos/{self.config.github.repository}/"
            f"commits/{self.config.github.commit_sha}/comments"
        )
        
        data = {"body": comment}
        
        with LogContext(logger, {
            "repository": self.config.github.repository,
            "commit_sha": self.config.github.commit_sha[:8]
        }):
            try:
                logger.info("💬 Posting comment to GitHub commit")
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        url,
                        headers=self.headers,
                        content=json.dumps(data),
                    )
                    response.raise_for_status()
                
                logger.info("✅ Comment posted successfully")
                return True
                
            except httpx.HTTPStatusError as e:
                error_msg = self._format_http_error(e)
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg, e.response.status_code)
            
            except httpx.TimeoutException:
                error_msg = "Request timeout - GitHub API is not responding"
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg)
            
            except Exception as e:
                error_msg = f"Unexpected error posting comment: {str(e)}"
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg)
    
    def _format_http_error(self, error: httpx.HTTPStatusError) -> str:
        """Format HTTP error with appropriate message."""
        status_code = error.response.status_code
        
        error_messages = {
            401: "Invalid or missing GitHub token",
            403: "API rate limit exceeded or insufficient permissions",
            404: f"Repository or commit not found: {self.config.github.repository}@{self.config.github.commit_sha[:8]}",
            422: "Invalid request data",
        }
        
        base_msg = error_messages.get(status_code, "API request failed")
        
        try:
            error_details = error.response.json()
            if "message" in error_details:
                base_msg += f" - {error_details['message']}"
        except Exception:
            pass
        
        return base_msg


class GitHubService:
    """Unified GitHub service combining Git and API operations."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.git_service = GitService(config)
        self.api_service = GitHubAPIService(config)
    
    def get_reviewable_files(self) -> Dict[str, str]:
        """Get all files that should be reviewed from the current commit."""
        logger.info("📝 Getting reviewable files from commit")
        
        changes = self.git_service.get_commit_changes()
        reviewable_changes = [c for c in changes if c.should_review]
        
        if not reviewable_changes:
            logger.info("📝 No reviewable files found")
            return {}
        
        result = {
            str(change.filepath): change.content
            for change in reviewable_changes
        }
        
        logger.info(f"✅ Found {len(result)} reviewable files")
        return result
    
    def post_review_comment(self, comment: str) -> bool:
        """Post a review comment to the commit."""
        return self.api_service.post_commit_comment(comment)


# Legacy support functions
def get_current_commit_diff() -> Dict[str, str]:
    """Legacy function for backward compatibility."""
    logger.warning("🚨 Using deprecated get_current_commit_diff function. Please migrate to GitHubService.")
    
    # For backward compatibility, we'll create a temporary config
    # This is not ideal but maintains compatibility
    import os
    from .config import AppConfig, GitHubConfig, LLMConfig, CrawlerConfig, LLMProvider
    
    try:
        temp_config = AppConfig(
            github=GitHubConfig(
                token=os.getenv("GITHUB_TOKEN", ""),
                repository=os.getenv("GITHUB_REPOSITORY", ""),
                commit_sha=os.getenv("GITHUB_SHA", "")
            ),
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4o",
                api_key="dummy"
            ),
            crawler=CrawlerConfig()
        )
        
        service = GitHubService(temp_config)
        return service.get_reviewable_files()
        
    except Exception as e:
        logger.error(f"❌ Legacy function failed: {e}")
        return {}


def write_comment_in_commit(comment: str) -> bool:
    """Legacy function for backward compatibility."""
    logger.warning("🚨 Using deprecated write_comment_in_commit function. Please migrate to GitHubService.")
    
    # For backward compatibility
    import os
    from .config import AppConfig, GitHubConfig, LLMConfig, CrawlerConfig, LLMProvider
    
    try:
        temp_config = AppConfig(
            github=GitHubConfig(
                token=os.getenv("GITHUB_TOKEN", ""),
                repository=os.getenv("GITHUB_REPOSITORY", ""),
                commit_sha=os.getenv("GITHUB_SHA", "")
            ),
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4o",
                api_key="dummy"
            ),
            crawler=CrawlerConfig()
        )
        
        service = GitHubService(temp_config)
        return service.post_review_comment(comment)
        
    except Exception as e:
        logger.error(f"❌ Legacy function failed: {e}")
        raise
