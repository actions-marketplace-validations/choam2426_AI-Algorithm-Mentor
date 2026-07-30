import json
import os

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from .config import GitHubConfig
from .consts import COMMENT_PREFIX_MAP, SUPPORT_FILE_EXTENSIONS
from .logger import logger

# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient failures that warrant a retry.

    Retryable conditions:
    - HTTP 5xx (server error)
    - HTTP 429 (rate-limited)
    - Connection errors and timeouts
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status >= 500 or status == 429
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))


_github_retry = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, log_level=30),  # WARNING
    reraise=True,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@_github_retry
def get_commit_data(config: GitHubConfig) -> dict:
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3.json",
    }
    url = (
        f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}"
    )

    response = httpx.get(url, headers=headers)
    response.raise_for_status()

    file_contents: dict[str, str] = {}
    commit_data = response.json()
    files = commit_data["files"]

    for file in files:
        filename = file["filename"]
        if not filename.endswith(SUPPORT_FILE_EXTENSIONS):
            continue

        try:
            content = _fetch_file_content(config, filename, headers)
        except Exception:
            logger.warning(
                "Skipping file %s: failed to fetch content", filename, exc_info=True
            )
            continue

        # Check if the first line is a comment
        _, ext = os.path.splitext(filename)
        prefixes = COMMENT_PREFIX_MAP.get(ext, ())

        # Skip if no comment prefixes defined or file is empty
        if not prefixes or not content.strip():
            continue

        first_line = content.lstrip().split("\n", 1)[0].strip()
        if not any(first_line.startswith(p) for p in prefixes):
            continue

        file_contents[filename] = content

    return file_contents


@_github_retry
def write_comment_in_commit(config: GitHubConfig, comment: str) -> None:
    url = f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}/comments"
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"body": comment}

    response = httpx.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()

    logger.info(
        "Comment posted on commit %s (status %d)",
        config.commit_sha[:7],
        response.status_code,
    )


@_github_retry
def get_readme_content(config: GitHubConfig, file_path: str) -> str | None:
    """
    리뷰 대상 파일과 같은 디렉토리의 README.md 파일 내용을 가져옵니다.

    Args:
        config: GitHub 설정
        file_path: 리뷰 대상 파일 경로 (예: "solutions/boj/1000/solution.py")

    Returns:
        README.md 내용 또는 None (존재하지 않거나 오류 시)
    """
    # 파일 경로에서 디렉토리 추출
    dir_path = os.path.dirname(file_path)
    readme_path = os.path.join(dir_path, "README.md").replace("\\", "/")

    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3.raw",
    }
    url = f"https://api.github.com/repos/{config.repository}/contents/{readme_path}"

    try:
        response = httpx.get(url, headers=headers)
        if response.status_code == 404:
            logger.info("README.md not found at %s", readme_path)
            return None
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError:
        logger.warning(
            "Failed to fetch README.md at %s", readme_path, exc_info=True
        )
        raise
    except Exception:
        logger.warning(
            "Unexpected error fetching README.md at %s", readme_path, exc_info=True
        )
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_file_content(
    config: GitHubConfig, filename: str, base_headers: dict[str, str]
) -> str:
    """Fetch raw file content from the GitHub Contents API.

    Raises on non-2xx responses so the caller can decide whether to skip.
    """
    url = f"https://api.github.com/repos/{config.repository}/contents/{filename}"
    content_headers = base_headers.copy()
    content_headers["Accept"] = "application/vnd.github.v3.raw"
    response = httpx.get(url, headers=content_headers)
    response.raise_for_status()
    return response.text
