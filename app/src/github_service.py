"""
GitHub integration service for AI Algorithm Mentor.

This module provides robust GitHub API integration with proper error handling,
type safety, and comprehensive logging for all GitHub operations.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from .config import AppConfig, CrawlerConfig, GitHubConfig, LLMConfig, LLMProvider
from .exceptions import FileProcessingError, GitHubAPIError
from .logger import LogContext, get_logger

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
            ".c",
            ".cpp",
            ".cc",
            ".cxx",
            ".py",
            ".java",
            ".js",
            ".go",
            ".rs",
        )
        return self.filepath.suffix.lower() in supported_extensions

    @property
    def should_review(self) -> bool:
        """Check if this file should be reviewed."""
        return self.status != "D" and self.is_source_file and self.content is not None


class GitHubService:
    """
    Unified service for GitHub operations, using the GitHub API for all interactions.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {config.github.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "AI-Algorithm-Mentor/1.0",
        }
        # Status mapping from GitHub API response to our internal representation
        self.status_map = {
            "added": "A",
            "modified": "M",
            "removed": "D",
            "renamed": "R",
        }

    def _get_commit_changes(self) -> List[FileChange]:
        """
        Get all file changes from the current commit using the GitHub API.
        This replaces the local 'git diff' command.
        """
        repo = self.config.github.repository
        sha = self.config.github.commit_sha
        log_ctx = {"repository": repo, "commit_sha": sha[:8]}

        with LogContext(logger, log_ctx):
            try:
                logger.info("🔍 Analyzing commit changes via GitHub API")
                with httpx.Client(timeout=30.0, headers=self.headers) as client:
                    # 1. Get commit details to find the parent commit SHA
                    commit_url = f"{self.base_url}/repos/{repo}/commits/{sha}"
                    commit_resp = client.get(commit_url)
                    commit_resp.raise_for_status()
                    commit_data = commit_resp.json()

                    if not commit_data.get("parents"):
                        # This is the initial commit, compare against an empty tree
                        # The files list in the commit data itself represents all added files
                        logger.info("🌱 Initial commit detected. Analyzing all files.")
                        api_files = commit_data.get("files", [])
                    else:
                        # 2. Compare the commit with its primary parent
                        parent_sha = commit_data["parents"][0]["sha"]
                        compare_url = (
                            f"{self.base_url}/repos/{repo}/compare/{parent_sha}...{sha}"
                        )
                        compare_resp = client.get(compare_url)
                        compare_resp.raise_for_status()
                        api_files = compare_resp.json().get("files", [])

                    if not api_files:
                        logger.info("📝 No file changes detected in API response.")
                        return []

                    # 3. Fetch content for each changed file
                    changes = self._fetch_file_contents(client, api_files)

                source_changes = [c for c in changes if c.is_source_file]
                logger.info(
                    f"✅ Found {len(changes)} total changes, "
                    f"{len(source_changes)} source files for review"
                )
                return changes

            except httpx.HTTPStatusError as e:
                error_msg = self._format_http_error(e)
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg, e.response.status_code) from e
            except httpx.TimeoutException as e:
                raise GitHubAPIError("GitHub API request timed out") from e
            except Exception as e:
                raise FileProcessingError(
                    f"Failed to get commit changes from API: {e}"
                ) from e

    def _fetch_file_contents(
        self, client: httpx.Client, api_files: List[Dict]
    ) -> List[FileChange]:
        """Fetch content for each file returned by the compare endpoint."""
        changes = []
        for file_data in api_files:
            status = self.status_map.get(file_data["status"], "M")
            filepath = Path(file_data["filename"])
            content = None

            # Fetch content only for non-deleted files
            if status != "D" and "raw_url" in file_data:
                try:
                    content_resp = client.get(file_data["raw_url"])
                    # Allow 404 for submodules or other unreadable content
                    if content_resp.status_code == 404:
                        logger.warning(
                            f"⚠️ Content not found for {filepath} (maybe a submodule?). Skipping."
                        )
                        continue
                    content_resp.raise_for_status()
                    content = content_resp.text
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"⚠️ Failed to fetch content for {filepath}: {e}. Skipping."
                    )
                    continue

            changes.append(
                FileChange(filepath=filepath, status=status, content=content)
            )
        return changes

    def get_reviewable_files(self) -> Dict[str, str]:
        """Get all files that should be reviewed from the current commit."""
        logger.info("📝 Getting reviewable files from commit")
        changes = self._get_commit_changes()
        reviewable_changes = [c for c in changes if c.should_review]

        if not reviewable_changes:
            logger.info("✅ No reviewable files found")
            return {}

        result = {str(c.filepath): c.content for c in reviewable_changes if c.content}
        logger.info(f"✅ Found {len(result)} reviewable files")
        return result

    def post_review_comment(self, comment: str) -> bool:
        """Post a review comment to the commit."""
        url = (
            f"{self.base_url}/repos/{self.config.github.repository}/"
            f"commits/{self.config.github.commit_sha}/comments"
        )
        data = {"body": comment}
        log_ctx = {
            "repository": self.config.github.repository,
            "commit_sha": self.config.github.commit_sha[:8],
        }

        with LogContext(logger, log_ctx):
            try:
                logger.info("💬 Posting comment to GitHub commit")
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        url, headers=self.headers, content=json.dumps(data)
                    )
                    response.raise_for_status()
                logger.info("✅ Comment posted successfully")
                return True
            except httpx.HTTPStatusError as e:
                error_msg = self._format_http_error(e)
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg, e.response.status_code) from e
            except httpx.TimeoutException as e:
                error_msg = "Request timeout - GitHub API is not responding"
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg) from e
            except Exception as e:
                error_msg = f"Unexpected error posting comment: {e}"
                logger.error(f"❌ {error_msg}")
                raise GitHubAPIError(error_msg) from e

    def _format_http_error(self, error: httpx.HTTPStatusError) -> str:
        """Format HTTP error with appropriate message."""
        status_code = error.response.status_code
        error_messages = {
            401: "Invalid or missing GitHub token",
            403: "API rate limit exceeded or insufficient permissions",
            404: f"Repository or commit not found: {self.config.github.repository}@{self.config.github.commit_sha[:8]}",
            422: "Invalid request data",
        }
        base_msg = error_messages.get(
            status_code, f"API request failed with status {status_code}"
        )
        try:
            error_details = error.response.json()
            if "message" in error_details:
                base_msg += f" - {error_details['message']}"
        except Exception:
            pass
        return base_msg


# Legacy support functions (updated to use the new unified GitHubService)


def _get_legacy_service() -> GitHubService:
    """Helper to create a GitHubService instance for legacy functions."""
    try:
        temp_config = AppConfig(
            github=GitHubConfig(
                token=os.getenv("GITHUB_TOKEN", ""),
                repository=os.getenv("GITHUB_REPOSITORY", ""),
                commit_sha=os.getenv("GITHUB_SHA", ""),
            ),
            llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o", api_key="dummy"),
            crawler=CrawlerConfig(),
        )
        return GitHubService(temp_config)
    except Exception as e:
        logger.error(f"❌ Failed to create service for legacy function: {e}")
        raise


def get_current_commit_diff() -> Dict[str, str]:
    """Legacy function for backward compatibility."""
    logger.warning(
        "🚨 Using deprecated get_current_commit_diff function. Please migrate to GitHubService."
    )
    try:
        service = _get_legacy_service()
        return service.get_reviewable_files()
    except Exception as e:
        logger.error(f"❌ Legacy function 'get_current_commit_diff' failed: {e}")
        return {}


def write_comment_in_commit(comment: str) -> bool:
    """Legacy function for backward compatibility."""
    logger.warning(
        "🚨 Using deprecated write_comment_in_commit function. Please migrate to GitHubService."
    )
    try:
        service = _get_legacy_service()
        return service.post_review_comment(comment)
    except Exception as e:
        logger.error(f"❌ Legacy function 'write_comment_in_commit' failed: {e}")
        return False
