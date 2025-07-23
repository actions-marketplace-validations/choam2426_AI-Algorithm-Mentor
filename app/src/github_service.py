import json
import subprocess

import httpx

from .consts import COMMIT_SHA, GITHUB_TOKEN, REPOSITORY_NAME

TARGET_SOURCE_FILE_SUFFIX = (
    ".c",
    ".cpp",
    "cc",
    "cxx",
    ".py",
    ".java",
    ".js",
    ".go",
    ".rs",
)


def get_current_commit_diff() -> dict[str, str]:
    file_contents = {}
    git_command = ["git", "diff", "--name-status", "HEAD~1", "HEAD"]
    try:
        output = subprocess.run(
            git_command, capture_output=True, text=True, check=True
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running git command: {e}")
        return {}
    for line in output.split("\n"):
        if not line.strip():
            continue

        parts = line.split("\t", 1)
        if len(parts) < 2:
            continue

        status, filepath = parts[0], parts[1]
        if status == "D":
            continue
        if filepath.endswith(TARGET_SOURCE_FILE_SUFFIX):
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    file_contents[filepath] = file.read()
            except FileNotFoundError:
                print(f"File not found: {filepath}")
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")

    return file_contents


def write_comment_in_commit(comment: str) -> None:
    url = (
        f"https://api.github.com/repos/{REPOSITORY_NAME}/commits/{COMMIT_SHA}/comments"
    )
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "GitHub-Actions-Bot",
    }
    data = {"body": comment}

    try:
        with httpx.Client(timeout=30.0) as client:  # 타임아웃 설정
            response = client.post(
                url,
                headers=headers,
                content=json.dumps(data),  # data → content, dumps 적용
            )
            response.raise_for_status()  # HTTP 에러 체크

        print(f"✅ Comment added to commit {COMMIT_SHA[:8]}")
        return True

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: "

        if e.response.status_code == 401:
            error_msg += "Invalid or missing GitHub token"
        elif e.response.status_code == 403:
            error_msg += "API rate limit exceeded or insufficient permissions"
        elif e.response.status_code == 404:
            error_msg += (
                f"Repository or commit not found: {REPOSITORY_NAME}@{COMMIT_SHA[:8]}"
            )
        elif e.response.status_code == 422:
            error_msg += "Invalid request data"
        else:
            error_msg += "API request failed"

        try:
            error_details = e.response.json()
            if "message" in error_details:
                error_msg += f" - {error_details['message']}"
        except:
            pass

        raise Exception(error_msg)

    except httpx.TimeoutException:
        raise Exception("Request timeout - GitHub API is not responding")
    except Exception as e:
        raise Exception(f"Failed to add comment: {str(e)}")
