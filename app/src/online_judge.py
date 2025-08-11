from __future__ import annotations

import re
from enum import Enum
from typing import Dict

from src.logger import logger
from src.problem_info_crawler import crawl_boj_problem_markdown


class OnlineJudgeSite(Enum):
    BOJ = "boj"
    PROGRAMMERS = "programmers"
    LEETCODE = "leetcode"


_PATTERNS: Dict[OnlineJudgeSite, re.Pattern[str]] = {
    OnlineJudgeSite.BOJ: re.compile(r"^https?://(?:www\.)?(?:acmicpc\.net/problem/\d+(?:\S*)?|boj\.kr/\d+)$", re.IGNORECASE),
    OnlineJudgeSite.PROGRAMMERS: re.compile(r"^https?://(?:school\.)?programmers\.co\.kr/learn/.*$", re.IGNORECASE),
    OnlineJudgeSite.LEETCODE: re.compile(r"^https?://(?:www\.)?(?:leetcode\.com|leetcode-cn\.com)/problems/[^/\s]+/?$", re.IGNORECASE),
}


def detect_online_judge(url: str) -> OnlineJudgeSite | None:
    """URL로 Online Judge 사이트를 감지합니다.

    지원: BOJ, Programmers, LeetCode
    """
    normalized = url.strip()
    for site, pattern in _PATTERNS.items():
        if pattern.match(normalized):
            return site
    return None


_URL_EXTRACTOR = re.compile(r"(https?://\S+)")


def extract_problem_info_from_changed_files(changed_files: Dict[str, str]) -> Dict[str, str]:
    """변경 파일의 첫 줄에서 URL을 추출해 OJ 사이트를 감지하고 문제 정보를 수집합니다.

    현재는 BOJ만 수집을 지원합니다.
    반환: { 파일경로: 문제정보(Markdown) }
    """
    results: Dict[str, str] = {}

    for path, content in changed_files.items():
        first_line = content.splitlines()[0] if content else ""
        m = _URL_EXTRACTOR.search(first_line)
        if not m:
            logger.info(f"skip (no URL on first line): {path}")
            continue

        url = m.group(1)
        site = detect_online_judge(url)
        if site is None:
            logger.info(f"skip (unsupported OJ): {path} -> {url}")
            continue

        logger.info(f"detected {site.value} url: {url} in {path}")

        try:
            if site is OnlineJudgeSite.BOJ:
                md = crawl_boj_problem_markdown(url)
            else:
                # TODO: Programmers / LeetCode 크롤러 연동 예정
                logger.info(f"collector not implemented for {site.value}, skip: {path}")
                continue
            results[path] = md
            logger.info(f"problem info fetched for {path}")
        except Exception as e:
            logger.error(f"failed to fetch problem info for {path}: {e}")

    return results

