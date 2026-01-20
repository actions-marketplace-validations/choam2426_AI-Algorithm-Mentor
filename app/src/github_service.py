import json
import os

import httpx

from .config import GitHubConfig
from .consts import COMMENT_PREFIX_MAP, SUPPORT_FILE_EXTENSIONS


def get_commit_data(config: GitHubConfig) -> dict:
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3.json",
    }
    url = (
        f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}"
    )
    response = httpx.get(url, headers=headers)
    file_contents = {}
    commit_data = response.json()
    files = commit_data["files"]
    for file in files:
        filename = file["filename"]
        if not filename.endswith(SUPPORT_FILE_EXTENSIONS):
            continue

        url = f"https://api.github.com/repos/{config.repository}/contents/{filename}"
        # Use raw header for file content to get the actual text
        content_headers = headers.copy()
        content_headers["Accept"] = "application/vnd.github.v3.raw"
        response = httpx.get(url, headers=content_headers)
        content = response.text

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


def write_comment_in_commit(config: GitHubConfig, comment: str) -> None:
    url = f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}/comments"
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"body": comment}

    response = httpx.post(url, headers=headers, data=json.dumps(data))


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
        if response.status_code == 200:
            return response.text
        return None
    except Exception:
        return None
