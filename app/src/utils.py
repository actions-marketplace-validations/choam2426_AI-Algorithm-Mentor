import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReadmeProblemInfo:
    """README.md에서 파싱한 문제 정보"""

    title: str
    url: str
    description: str
    input_desc: str
    output_desc: str
    tags: list[str]
    difficulty: str | None = None


def parse_readme_as_problem(readme_content: str) -> ReadmeProblemInfo | None:
    """
    solved.ac 형식의 README.md를 파싱하여 문제 정보를 추출합니다.

    예시 형식:
    # [Gold V] 하노이 탑 이동 순서 - 11729
    [문제 링크](https://www.acmicpc.net/problem/11729)
    ### 분류
    재귀
    ### 문제 설명
    <p>...</p>
    ### 입력
    <p>...</p>
    ### 출력
    <p>...</p>
    """
    if not readme_content or not readme_content.strip():
        return None

    lines = readme_content.strip().split("\n")

    # 제목 파싱: # [난이도] 문제명 - 번호
    title_pattern = r"^#\s+\[([^\]]+)\]\s+(.+?)\s*-\s*(\d+)\s*$"
    title_match = re.match(title_pattern, lines[0].strip())
    if not title_match:
        return None

    difficulty = title_match.group(1)
    problem_name = title_match.group(2).strip()
    problem_id = title_match.group(3)
    title = f"{problem_name} - {problem_id}"

    # URL 파싱
    url_pattern = r"\[문제 링크\]\((https?://[^\)]+)\)"
    url_match = re.search(url_pattern, readme_content)
    url = url_match.group(1) if url_match else ""

    # 섹션 추출 헬퍼 함수
    def extract_section(section_name: str) -> str:
        pattern = rf"###\s+{re.escape(section_name)}\s*\n(.*?)(?=###\s+|\Z)"
        match = re.search(pattern, readme_content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    # 각 섹션 추출
    description = extract_section("문제 설명")
    input_desc = extract_section("입력")
    output_desc = extract_section("출력")

    # 분류(태그) 추출
    tags_section = extract_section("분류")
    tags = [tag.strip() for tag in tags_section.split(",") if tag.strip()] if tags_section else []
    # 줄바꿈으로 구분된 경우도 처리
    if not tags and tags_section:
        tags = [tag.strip() for tag in tags_section.split("\n") if tag.strip()]

    # 최소한 문제 설명이 있어야 유효한 README로 간주
    if not description:
        return None

    return ReadmeProblemInfo(
        title=title,
        url=url,
        description=description,
        input_desc=input_desc,
        output_desc=output_desc,
        tags=tags,
        difficulty=difficulty,
    )


def parse_problem_url(content: str) -> Optional[tuple[str, str]]:
    """
    Extracts the problem platform and ID/URL from the given content (usually source code).
    Returns a tuple of (platform_name, problem_id).
    """

    # BOJ: https://www.acmicpc.net/problem/1234
    boj_pattern = r"acmicpc\.net/problem/(\d+)"
    match = re.search(boj_pattern, content)
    if match:
        return "BOJ", match.group(1)

    # LeetCode: https://leetcode.com/problems/two-sum/
    leetcode_pattern = r"leetcode\.com/problems/([^/]+)"
    match = re.search(leetcode_pattern, content)
    if match:
        return "LeetCode", match.group(1)

    # Programmers: https://school.programmers.co.kr/learn/courses/30/lessons/12345
    programmers_pattern = r"school\.programmers\.co\.kr/learn/courses/30/lessons/(\d+)"
    match = re.search(programmers_pattern, content)
    if match:
        return "Programmers", match.group(1)

    return None
