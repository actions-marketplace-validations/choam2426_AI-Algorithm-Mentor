import json

import requests

from .config import GitHubConfig
from .consts import SUPPORT_FILE_EXTENSIONS


def get_commit_data(config: GitHubConfig) -> dict:
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3.json",
    }
    url = f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}"
    response = requests.get(url, headers=headers)
    file_contents = {}
    commit_data = response.json()
    files = commit_data["files"]
    for file in files:
        filename = file["filename"]
        if not filename.endswith(SUPPORT_FILE_EXTENSIONS):
            continue

        url = f"https://api.github.com/repos/{config.repository}/contents/{filename}"
        response = requests.get(url, headers=headers)
        file_contents[filename] = response.text
    return file_contents


def write_comment_in_commit(config: GitHubConfig, comment: str) -> None:
    url = f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}/comments"
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"body": comment}

    response = requests.post(url, headers=headers, data=json.dumps(data))
