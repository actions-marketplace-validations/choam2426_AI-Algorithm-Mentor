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
    """Clone the full repository and checkout the target commit in a temp dir."""
    if not config.repository:
        raise ValueError("GITHUB_REPOSITORY 환경 변수가 설정되지 않았습니다.")
    if not config.commit_sha:
        raise ValueError("GITHUB_SHA 환경 변수가 설정되지 않았습니다.")

    workdir = _safe_tmp_dir()
    logger.info(f"clone workspace: {workdir}")

    # Clone full repository into the workspace (do not print token)
    remote_url = f"https://{config.github_token}@github.com/{config.repository}.git"
    code, out, err = _run_git(["clone", remote_url, "."], cwd=workdir)
    if code != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"git clone 실패: {err}")

    # Ensure the target commit exists locally (fetch by SHA)
    code, out, err = _run_git(["fetch", "origin", config.commit_sha], cwd=workdir)
    if code != 0:
        logger.warning(f"git fetch by sha failed, proceeding to checkout: {err}")

    # Checkout the target commit
    code, out, err = _run_git(["checkout", config.commit_sha], cwd=workdir)
    if code != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"git checkout 실패: {err}")

    logger.info("repository fully cloned and checked out at target commit")
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

    - Merge/일반 커밋: 첫 부모와의 `git diff --name-status -z` 사용
    - 초기 커밋: `git diff-tree --root -r --name-status -z` 사용
    - 삭제 파일은 제외, 지원 확장자만 포함
    - 리네임은 새 경로만 포함
    """
    def parse_name_status_null_separated(name_status_output: str) -> list[tuple[str, str]]:
        tokens = name_status_output.split("\x00")
        i = 0
        pairs: list[tuple[str, str]] = []
        while i < len(tokens):
            status = tokens[i]
            if not status:
                break
            if status.startswith("R"):
                # status, old, new
                if i + 2 < len(tokens):
                    new_path = tokens[i + 2]
                    if new_path:
                        pairs.append(("R", new_path))
                i += 3
            else:
                # status, path
                if i + 1 < len(tokens):
                    path = tokens[i + 1]
                    if path:
                        pairs.append((status, path))
                i += 2
        return pairs

    # Find parents
    code, parents_line, err = _run_git(["rev-list", "--parents", "-n", "1", commit_sha], cwd=repo_dir)
    parents: list[str] = []
    if code == 0 and parents_line:
        parts = parents_line.strip().split()
        parents = parts[1:]  # parts[0] is commit itself

    results: Dict[str, str] = {}

    changed_spec: list[tuple[str, str]] = []
    if not parents:
        # Initial commit: diff-tree against empty tree
        logger.info("initial commit detected; using diff-tree --root")
        code, out, err = _run_git([
            "diff-tree", "--root", "--no-commit-id", "--name-status", "-z", "-r", commit_sha
        ], cwd=repo_dir)
        if code != 0:
            raise RuntimeError(f"git diff-tree 실패: {err}")
        changed_spec = parse_name_status_null_separated(out)
    else:
        # Diff against first parent
        parent = parents[0]
        logger.info(f"diff against parent {parent[:8]}")
        code, out, err = _run_git([
            "diff", "--name-status", "-z", parent, commit_sha
        ], cwd=repo_dir)
        if code != 0 or not out:
            logger.warning(f"git diff failed or empty, fallback to diff-tree: {err}")
            code, out, err = _run_git([
                "diff-tree", "--no-commit-id", "--name-status", "-z", "-r", commit_sha
            ], cwd=repo_dir)
            if code != 0:
                raise RuntimeError(f"git diff-tree 실패: {err}")
        changed_spec = parse_name_status_null_separated(out)

    for status, rel_path in changed_spec:
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

    if not results:
        logger.warning("no supported changed files detected for the commit")
    return results


def fetch_changed_files_for_commit(config: GitHubConfig) -> Dict[str, str]:
    """커밋 변경 파일을 {path: content}로 반환 (로컬 git 클론 방식)."""
    if not config.repository:
        raise ValueError("GITHUB_REPOSITORY 환경 변수가 설정되지 않았습니다.")
    if not config.commit_sha:
        raise ValueError("GITHUB_SHA 환경 변수가 설정되지 않았습니다.")

    logger.info(
        f"start fetching changed files via local git: repo={config.repository}, sha={config.commit_sha[:8]}"
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
