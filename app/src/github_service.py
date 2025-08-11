from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Tuple
import httpx

from .config import GitHubConfig
from .consts import SURPORT_FILE_EXTENSIONS
from .logger import logger


def _run_git(args: Iterable[str], cwd: Path) -> Tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    process = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return process.returncode, process.stdout.strip(), process.stderr.strip()


def _safe_tmp_dir(prefix: str = "gh_repo_") -> Path:
    base_tmp = Path(tempfile.mkdtemp(prefix=prefix))
    return base_tmp


def clone_commit_to_temp(config: GitHubConfig) -> Path:
    """Shallow-fetch a specific commit into a temporary working directory.

    Steps:
    1) git init
    2) git remote add origin https://<token>@github.com/<owner>/<repo>.git
    3) git fetch --depth=1 origin <commit_sha>
    4) git checkout FETCH_HEAD
    """
    if not config.repository:
        raise ValueError("GITHUB_REPOSITORY 환경 변수가 설정되지 않았습니다.")
    if not config.commit_sha:
        raise ValueError("GITHUB_SHA 환경 변수가 설정되지 않았습니다.")

    workdir = _safe_tmp_dir()
    logger.info(f"clone workspace: {workdir}")

    # Initialize empty repo
    code, out, err = _run_git(["init"], cwd=workdir)
    if code != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"git init 실패: {err}")

    # Add remote with token (avoid printing token)
    remote_url = f"https://{config.github_token}@github.com/{config.repository}.git"
    code, out, err = _run_git(["remote", "add", "origin", remote_url], cwd=workdir)
    if code != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"git remote add 실패: {err}")

    # Fetch specific commit
    code, out, err = _run_git(["fetch", "--depth=1", "origin", config.commit_sha], cwd=workdir)
    if code != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"git fetch 실패: {err}")

    # Checkout fetched commit
    code, out, err = _run_git(["checkout", "FETCH_HEAD"], cwd=workdir)
    if code != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"git checkout 실패: {err}")

    logger.info("repository cloned at specific commit")
    return workdir


def _parse_changed_files_from_show(output: str) -> Iterable[Tuple[str, str]]:
    """Parse lines from `git show --name-status <sha>`.

    Returns iterable of (status, path). For rename, returns ("R", new_path).
    """
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        # status formats:
        # A <path>
        # M <path>
        # D <path>
        # R100 <old> <new>
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R"):
            # rename: status, old, new
            if len(parts) >= 3:
                yield ("R", parts[2])
        elif status in {"A", "M", "D", "C"}:
            if len(parts) >= 2:
                yield (status, parts[1])


def _is_supported_file(path: str) -> bool:
    return any(path.endswith(ext) for ext in SURPORT_FILE_EXTENSIONS)


def get_changed_files_at_commit(repo_dir: Path, commit_sha: str) -> Dict[str, str]:
    """Return mapping of {relative_path: content} for files changed in commit.

    Only includes files with extensions in SURPORT_FILE_EXTENSIONS and that exist
    at the specified commit (deleted files are skipped).
    """
    code, out, err = _run_git(["show", "--name-status", "--pretty=format:", commit_sha], cwd=repo_dir)
    if code != 0:
        raise RuntimeError(f"git show 실패: {err}")

    changed = list(_parse_changed_files_from_show(out))
    results: Dict[str, str] = {}

    for status, rel_path in changed:
        if status == "D":
            continue  # deleted in this commit -> skip
        if not _is_supported_file(rel_path):
            continue
        abs_path = repo_dir / rel_path
        if not abs_path.exists():
            # In rare cases (e.g., rename to path not present?), fallback to blob read
            code, blob, err = _run_git(["show", f"{commit_sha}:{rel_path}"], cwd=repo_dir)
            if code == 0:
                results[rel_path] = blob
            continue
        try:
            text = abs_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = abs_path.read_text(encoding="utf-8", errors="ignore")
        results[rel_path] = text

    return results


def fetch_changed_files_for_commit(config: GitHubConfig) -> Dict[str, str]:
    """클론 → 변경 파일 수집 → 정리까지 하나로 수행하는 고수준 함수.

    내부적으로 보조 함수(`clone_commit_to_temp`, `get_changed_files_at_commit`)를 사용합니다.
    """
    if not config.repository:
        raise ValueError("GITHUB_REPOSITORY 환경 변수가 설정되지 않았습니다.")
    if not config.commit_sha:
        raise ValueError("GITHUB_SHA 환경 변수가 설정되지 않았습니다.")

    logger.info(
        f"start fetching changed files: repo={config.repository}, sha={config.commit_sha[:8]}"
    )
    repo_dir = clone_commit_to_temp(config)
    try:
        results = get_changed_files_at_commit(repo_dir, config.commit_sha)
        logger.info(f"📝 collected {len(results)} supported changed files")
        return results
    finally:
        try:
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info("🧹 temp workspace cleaned up")
        except Exception:
            pass


def post_commit_comment(config: GitHubConfig, comment: str) -> bool:
    """GitHub API를 사용해서 특정 커밋에 코멘트를 남깁니다.

    Parameters
    ----------
    config: GitHubConfig
        repository ("owner/repo"), commit_sha, github_token을 포함해야 합니다.
    comment: str
        코멘트 본문 텍스트

    Returns
    -------
    bool
        성공 시 True, 실패 시 False
    """
    if not config.github_token:
        raise ValueError("GITHUB_TOKEN 누락: 코멘트를 전송할 수 없습니다.")
    if not config.repository:
        raise ValueError("GITHUB_REPOSITORY 누락: 코멘트를 전송할 수 없습니다.")
    if not config.commit_sha:
        raise ValueError("GITHUB_SHA 누락: 코멘트를 전송할 수 없습니다.")

    url = (
        f"https://api.github.com/repos/{config.repository}/commits/{config.commit_sha}/comments"
    )
    headers = {
        "Authorization": f"token {config.github_token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "AI-Algorithm-Mentor/1.0",
    }

    payload = {"body": comment}

    logger.info(
        f"💬 posting comment to {config.repository}@{config.commit_sha[:8]}"
    )
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
        logger.info("✅ comment posted successfully")
        return True
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else "?"
        logger.error(f"❌ failed to post comment (status={status}): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ unexpected error while posting comment: {e}")
        return False
