import pytest

from src.utils import ReadmeProblemInfo, parse_problem_url, parse_readme_as_problem


class TestParseProblemUrl:
    """Tests for parse_problem_url function."""

    @pytest.mark.parametrize(
        "content, expected",
        [
            (
                "# https://www.acmicpc.net/problem/1000",
                ("BOJ", "1000"),
            ),
            (
                "// https://leetcode.com/problems/two-sum/",
                ("LeetCode", "two-sum"),
            ),
            (
                "// https://school.programmers.co.kr/learn/courses/30/lessons/12345",
                ("Programmers", "12345"),
            ),
        ],
        ids=["boj", "leetcode", "programmers"],
    )
    def test_valid_urls(self, content, expected):
        result = parse_problem_url(content)
        assert result == expected

    def test_no_match_returns_none(self):
        assert parse_problem_url('print("hello")') is None

    def test_empty_string(self):
        assert parse_problem_url("") is None

    def test_url_embedded_in_multiline_code(self):
        content = """
import sys
# Problem: https://www.acmicpc.net/problem/2557
n = int(input())
print(n)
"""
        result = parse_problem_url(content)
        assert result == ("BOJ", "2557")

    def test_boj_url_with_large_id(self):
        content = "# https://www.acmicpc.net/problem/99999"
        assert parse_problem_url(content) == ("BOJ", "99999")

    def test_leetcode_slug_with_hyphens(self):
        content = "// https://leetcode.com/problems/longest-common-subsequence/"
        assert parse_problem_url(content) == ("LeetCode", "longest-common-subsequence")

    def test_first_match_wins_when_multiple_urls(self):
        content = """
# https://www.acmicpc.net/problem/1000
# https://www.acmicpc.net/problem/2000
"""
        result = parse_problem_url(content)
        assert result == ("BOJ", "1000")


class TestParseReadmeAsProblem:
    """Tests for parse_readme_as_problem function."""

    def test_valid_readme(self, boj_readme_content):
        result = parse_readme_as_problem(boj_readme_content)

        assert result is not None
        assert isinstance(result, ReadmeProblemInfo)
        assert result.title == "하노이 탑 이동 순서 - 11729"
        assert result.url == "https://www.acmicpc.net/problem/11729"
        assert result.difficulty == "Gold V"
        assert "재귀" in result.tags
        assert result.description != ""
        assert result.input_desc != ""
        assert result.output_desc != ""

    def test_empty_input_returns_none(self):
        assert parse_readme_as_problem("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_readme_as_problem("   \n\n  ") is None

    def test_none_input_returns_none(self):
        assert parse_readme_as_problem(None) is None

    def test_missing_description_returns_none(self):
        content = """# [Gold V] 하노이 탑 이동 순서 - 11729

[문제 링크](https://www.acmicpc.net/problem/11729)

### 분류

재귀
"""
        assert parse_readme_as_problem(content) is None

    def test_invalid_title_format_returns_none(self):
        content = """# Some random title without proper format

### 문제 설명

Some description here
"""
        assert parse_readme_as_problem(content) is None

    def test_comma_separated_tags(self):
        content = """# [Silver I] 테스트 문제 - 9999

[문제 링크](https://www.acmicpc.net/problem/9999)

### 분류

구현, 수학, 문자열

### 문제 설명

<p>테스트 문제입니다.</p>

### 입력

<p>없음</p>

### 출력

<p>없음</p>
"""
        result = parse_readme_as_problem(content)
        assert result is not None
        assert "구현" in result.tags
        assert "수학" in result.tags
        assert "문자열" in result.tags
