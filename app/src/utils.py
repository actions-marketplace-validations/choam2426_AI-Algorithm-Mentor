import re
from typing import Optional


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
