import pytest


@pytest.fixture
def boj_readme_content():
    """Solved.ac style README.md content for testing."""
    return """# [Gold V] 하노이 탑 이동 순서 - 11729

[문제 링크](https://www.acmicpc.net/problem/11729)

### 분류

재귀

### 문제 설명

<p>세 개의 장대가 있고 첫 번째 장대에 반지름이 서로 다른 n개의 원판이 쌓여 있다.</p>

### 입력

<p>첫째 줄에 첫 번째 장대에 쌓인 원판의 개수 N (1 <= N <= 20)이 주어진다.</p>

### 출력

<p>첫째 줄에 옮긴 횟수 K를 출력한다.</p>
"""


@pytest.fixture
def boj_problem_html():
    """Minimal BOJ problem page HTML for testing scraper parsing."""
    return """
<html>
<head><title>1000번: A+B</title></head>
<body>
<span id="problem_title">A+B</span>
<table id="problem-info">
  <thead><tr><th>시간 제한</th><th>메모리 제한</th></tr></thead>
  <tbody><tr><td>2 초</td><td>128 MB</td></tr></tbody>
</table>
<div id="problem_description"><p>두 정수 A와 B를 입력받은 다음, A+B를 출력하는 프로그램을 작성하시오.</p></div>
<div id="problem_input"><p>첫째 줄에 A와 B가 주어진다. (0 < A, B < 10)</p></div>
<div id="problem_output"><p>첫째 줄에 A+B를 출력한다.</p></div>
<pre id="sample-input-1">1 2
</pre>
<pre id="sample-output-1">3
</pre>
<pre id="sample-input-2">3 4
</pre>
<pre id="sample-output-2">7
</pre>
<div id="problem_tags">
  <ul>
    <li><a>수학</a></li>
    <li><a>구현</a></li>
  </ul>
</div>
</body>
</html>
"""
