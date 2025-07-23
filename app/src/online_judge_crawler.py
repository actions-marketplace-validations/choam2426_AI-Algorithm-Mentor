import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class ProblemInfo:
    """문제 정보를 담는 데이터 클래스"""

    site: str
    problem_id: str
    title: str
    difficulty: Optional[str] = None
    description: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    examples: List[Dict[str, str]] = field(default_factory=list)
    time_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    url: str = None
    success: bool = True
    error_message: Optional[str] = None


class MultiSiteSeleniumCrawler:
    """셀레니움 기반 5대 온라인 저지 사이트 크롤러"""

    # 지원 사이트 목록
    SUPPORTED_SITES = {
        "acmicpc.net": "Baekjoon",
        "programmers.co.kr": "Programmers",
        "leetcode.com": "LeetCode",
        "codeforces.com": "Codeforces",
        "hackerrank.com": "HackerRank",
    }

    def __init__(self, headless=True, timeout=15):
        self.timeout = timeout
        self.headless = headless
        self.driver = None
        self.wait = None
        self._setup_driver()

    def _setup_driver(self):
        """Chrome 드라이버 설정"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")  # 새로운 headless 모드

        # 성능 최적화 옵션들
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(
            "--disable-images"
        )  # 이미지 로딩 차단으로 속도 향상
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 메모리 사용량 최적화
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            self.wait = WebDriverWait(self.driver, self.timeout)
            print("✅ Chrome 드라이버 초기화 완료")
        except Exception as e:
            raise Exception(
                f"❌ Chrome 드라이버 설정 실패: {e}\n💡 chromedriver가 설치되어 있는지 확인하세요."
            )

    def get_site_name(self, url: str) -> str:
        """URL에서 사이트명 추출"""
        try:
            domain = urlparse(url).netloc.lower()
            # www. 제거
            if domain.startswith("www."):
                domain = domain[4:]

            for site_domain, site_name in self.SUPPORTED_SITES.items():
                if site_domain in domain:
                    return site_name

            return domain
        except:
            return "Unknown"

    def is_supported_site(self, url: str) -> bool:
        """지원하는 사이트인지 확인"""
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        return any(site_domain in domain for site_domain in self.SUPPORTED_SITES.keys())

    def crawl_problem(self, url: str) -> ProblemInfo:
        """URL에서 문제 정보 크롤링"""
        if not self.is_supported_site(url):
            return ProblemInfo(
                site="Unknown",
                problem_id="unknown",
                title="지원하지 않는 사이트",
                url=url,
                success=False,
                error_message=f"지원하지 않는 사이트입니다. 지원 사이트: {', '.join(self.SUPPORTED_SITES.values())}",
            )

        site_name = self.get_site_name(url)
        print(f"🔍 {site_name} 크롤링 시작: {url}")

        try:
            if "acmicpc.net" in url:
                return self._crawl_baekjoon(url)
            elif "programmers.co.kr" in url:
                return self._crawl_programmers(url)
            elif "leetcode.com" in url:
                return self._crawl_leetcode(url)
            elif "codeforces.com" in url:
                return self._crawl_codeforces(url)
            elif "hackerrank.com" in url:
                return self._crawl_hackerrank(url)
            else:
                return ProblemInfo(
                    site=site_name,
                    problem_id="unknown",
                    title="지원하지 않는 사이트",
                    url=url,
                    success=False,
                    error_message="해당 사이트는 아직 구현되지 않았습니다",
                )

        except Exception as e:
            return ProblemInfo(
                site=site_name,
                problem_id="error",
                title="크롤링 실패",
                url=url,
                success=False,
                error_message=f"{site_name} 크롤링 중 오류: {str(e)}",
            )

    def _crawl_baekjoon(self, url: str) -> ProblemInfo:
        """백준 문제 크롤링"""
        self.driver.get(url)

        # 문제 번호 추출
        problem_id = re.search(r"/problem/(\d+)", url).group(1)

        # 문제 제목
        title = self.wait.until(
            EC.presence_of_element_located((By.ID, "problem_title"))
        ).text.strip()

        # 문제 설명
        try:
            description_elem = self.driver.find_element(By.ID, "problem_description")
            description = description_elem.text.strip()
        except:
            description = None

        # 입출력 설명
        try:
            input_elem = self.driver.find_element(By.ID, "problem_input")
            input_format = input_elem.text.strip()
        except:
            input_format = None

        try:
            output_elem = self.driver.find_element(By.ID, "problem_output")
            output_format = output_elem.text.strip()
        except:
            output_format = None

        # 예제 입출력
        examples = []
        try:
            sample_inputs = self.driver.find_elements(
                By.CSS_SELECTOR, "pre[id^='sample-input-']"
            )
            sample_outputs = self.driver.find_elements(
                By.CSS_SELECTOR, "pre[id^='sample-output-']"
            )

            for inp, out in zip(sample_inputs, sample_outputs):
                examples.append({"input": inp.text.strip(), "output": out.text.strip()})
        except:
            pass

        # 시간/메모리 제한
        time_limit = memory_limit = None
        try:
            info_table = self.driver.find_element(By.ID, "problem-info")
            rows = info_table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    cell_text = cells[0].text.strip()
                    if "시간" in cell_text:
                        time_limit = cells[1].text.strip()
                    elif "메모리" in cell_text:
                        memory_limit = cells[1].text.strip()
        except:
            pass

        return ProblemInfo(
            site="Baekjoon",
            problem_id=problem_id,
            title=title,
            description=description,
            input_format=input_format,
            output_format=output_format,
            examples=examples,
            time_limit=time_limit,
            memory_limit=memory_limit,
            url=url,
        )

    def _crawl_programmers(self, url: str) -> ProblemInfo:
        """프로그래머스 문제 크롤링"""
        self.driver.get(url)
        time.sleep(5)  # JavaScript 로딩 대기

        # 문제 ID 추출
        problem_id = re.search(r"/lessons/(\d+)", url)
        problem_id = problem_id.group(1) if problem_id else "unknown"

        # 문제 제목 - 여러 선택자 시도
        title = "제목 추출 실패"
        title_selectors = [
            "h3.lesson-title",
            ".algorithm-title",
            "[data-cy='algorithm-title']",
            ".title",
            "h1",
            "h2",
            "h3",
            ".challenge-title",
        ]

        for selector in title_selectors:
            try:
                title_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                potential_title = title_elem.text.strip()
                if (
                    potential_title
                    and not potential_title.startswith("프로그래머스")
                    and len(potential_title) > 3
                ):
                    title = potential_title
                    break
            except:
                continue

        # 난이도 추출
        difficulty = None
        difficulty_selectors = [
            ".algorithm-level",
            ".level",
            "[class*='level']",
            ".difficulty",
            "[data-testid='level']",
        ]

        for selector in difficulty_selectors:
            try:
                diff_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                difficulty = diff_elem.text.strip()
                if difficulty and "Level" in difficulty:
                    break
            except:
                continue

        # 문제 설명 - 부분적으로만 추출 가능
        description = None
        desc_selectors = [
            ".guide-section-description",
            ".algorithm-description",
            ".lesson-content",
            "[data-cy='algorithm-description']",
            ".content",
            ".markdown",
        ]

        for selector in desc_selectors:
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_elem.text.strip()
                if desc_text and len(desc_text) > 10:
                    description = desc_text[:800]  # 처음 800자만
                    break
            except:
                continue

        return ProblemInfo(
            site="Programmers",
            problem_id=problem_id,
            title=title,
            difficulty=difficulty,
            description=description,
            url=url,
        )

    def _crawl_leetcode(self, url: str) -> ProblemInfo:
        """리트코드 문제 크롤링"""
        self.driver.get(url)
        time.sleep(8)  # GraphQL 및 React 로딩 대기

        # 문제 ID 추출
        problem_match = re.search(r"/problems/([^/]+)", url)
        problem_id = problem_match.group(1) if problem_match else "unknown"

        # 문제 제목
        title = "제목 추출 실패"
        title_selectors = [
            "[data-cy='question-title']",
            ".text-title-large",
            ".mr-2",
            "h1",
            ".css-v3d350",
            ".question-title",
        ]

        for selector in title_selectors:
            try:
                title_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                potential_title = title_elem.text.strip()
                if (
                    potential_title
                    and not potential_title.startswith("Sign")
                    and len(potential_title) > 3
                ):
                    # 문제 번호가 포함된 경우 제거
                    clean_title = re.sub(r"^\d+\.\s*", "", potential_title)
                    title = clean_title if clean_title else potential_title
                    break
            except:
                continue

        # 난이도
        difficulty = None
        diff_selectors = [
            ".text-olive",  # Easy
            ".text-yellow",  # Medium
            ".text-pink",  # Hard
            "[diff='1']",
            "[diff='2']",
            "[diff='3']",
            ".difficulty",
        ]

        for selector in diff_selectors:
            try:
                diff_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if "olive" in selector:
                    difficulty = "Easy"
                elif "yellow" in selector:
                    difficulty = "Medium"
                elif "pink" in selector:
                    difficulty = "Hard"
                else:
                    difficulty = diff_elem.text.strip()

                if difficulty:
                    break
            except:
                continue

        # 문제 설명 (제한적)
        description = None
        desc_selectors = [
            ".question-content",
            ".content__u3I1",
            "[data-track-load='description_content']",
            ".elfjS",
        ]

        for selector in desc_selectors:
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_elem.text.strip()
                if desc_text and len(desc_text) > 20:
                    description = desc_text[:1000]  # 처음 1000자만
                    break
            except:
                continue

        if not description:
            description = "로그인이 필요하거나 JavaScript 렌더링 지연으로 인해 상세 정보 추출 제한"

        return ProblemInfo(
            site="LeetCode",
            problem_id=problem_id,
            title=title,
            difficulty=difficulty,
            description=description,
            url=url,
        )

    def _crawl_codeforces(self, url: str) -> ProblemInfo:
        """코드포스 문제 크롤링"""
        self.driver.get(url)

        # 문제 ID 추출
        problem_match = re.search(r"/problem/([^/]+/[^/]+)", url)
        if not problem_match:
            problem_match = re.search(r"/contest/(\d+)/problem/([A-Z]+)", url)
            problem_id = (
                f"{problem_match.group(1)}{problem_match.group(2)}"
                if problem_match
                else "unknown"
            )
        else:
            problem_id = problem_match.group(1)

        # 문제 제목
        title = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".problem-statement .title")
            )
        ).text.strip()

        # 시간/메모리 제한
        time_limit = memory_limit = None
        try:
            time_elem = self.driver.find_element(By.CSS_SELECTOR, ".time-limit")
            time_limit = time_elem.text.strip()
        except:
            pass

        try:
            memory_elem = self.driver.find_element(By.CSS_SELECTOR, ".memory-limit")
            memory_limit = memory_elem.text.strip()
        except:
            pass

        # 문제 설명
        description = None
        try:
            desc_elem = self.driver.find_element(By.CSS_SELECTOR, ".problem-statement")
            paragraphs = desc_elem.find_elements(By.TAG_NAME, "p")
            if paragraphs:
                description = paragraphs[0].text.strip()[
                    :800
                ]  # 첫 번째 문단, 800자 제한
        except:
            pass

        # 예제 입출력
        examples = []
        try:
            input_elems = self.driver.find_elements(By.CSS_SELECTOR, ".input pre")
            output_elems = self.driver.find_elements(By.CSS_SELECTOR, ".output pre")

            for inp, out in zip(input_elems, output_elems):
                examples.append({"input": inp.text.strip(), "output": out.text.strip()})
        except:
            pass

        return ProblemInfo(
            site="Codeforces",
            problem_id=problem_id,
            title=title,
            description=description,
            examples=examples,
            time_limit=time_limit,
            memory_limit=memory_limit,
            url=url,
        )

    def _crawl_hackerrank(self, url: str) -> ProblemInfo:
        """해커랭크 문제 크롤링"""
        self.driver.get(url)
        time.sleep(5)  # 페이지 로딩 대기

        # 문제 ID 추출
        problem_match = re.search(r"/challenges/([^/]+)", url)
        problem_id = problem_match.group(1) if problem_match else "unknown"

        # 문제 제목
        title = "제목 추출 실패"
        title_selectors = [
            ".challenge-name",
            ".challenge-title",
            "h1.ui-icon-label",
            ".page-header-text",
            "h1",
        ]

        for selector in title_selectors:
            try:
                title_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                potential_title = title_elem.text.strip()
                if potential_title and len(potential_title) > 3:
                    title = potential_title
                    break
            except:
                continue

        # 난이도
        difficulty = None
        diff_selectors = [
            ".difficulty",
            ".challenge-difficulty",
            "[class*='difficulty']",
        ]

        for selector in diff_selectors:
            try:
                diff_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                difficulty = diff_elem.text.strip()
                if difficulty:
                    break
            except:
                continue

        # 문제 설명 (제한적)
        description = None
        desc_selectors = [
            ".challenge-text",
            ".problem-statement",
            ".challenge-body-html",
            ".content",
        ]

        for selector in desc_selectors:
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_elem.text.strip()
                if desc_text and len(desc_text) > 20:
                    description = desc_text[:800]  # 처음 800자만
                    break
            except:
                continue

        return ProblemInfo(
            site="HackerRank",
            problem_id=problem_id,
            title=title,
            difficulty=difficulty,
            description=description,
            url=url,
        )

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            print("🔴 Chrome 드라이버 종료")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# URL 추출 함수 (이전 코드에서 가져옴)
def extract_online_judge_urls(text: str) -> Dict[str, List[str]]:
    """문장에서 온라인 저지 URL을 추출하는 함수"""
    import re

    # 온라인 저지 사이트 도메인 정의
    ONLINE_JUDGE_DOMAINS = {
        "acmicpc.net": "Baekjoon",
        "www.acmicpc.net": "Baekjoon",
        "programmers.co.kr": "Programmers",
        "school.programmers.co.kr": "Programmers",
        "leetcode.com": "LeetCode",
        "www.leetcode.com": "LeetCode",
        "codeforces.com": "Codeforces",
        "www.codeforces.com": "Codeforces",
        "hackerrank.com": "HackerRank",
        "www.hackerrank.com": "HackerRank",
    }

    # URL 패턴 정규식
    url_pattern = (
        r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+\.[a-zA-Z]{2,}'
    )

    # 모든 URL 찾기
    urls = re.findall(url_pattern, text)
    urls = list(set(urls))  # 중복 제거

    online_judge_urls = []
    online_judge_sites = []

    for url in urls:
        if url.startswith("www."):
            url = "http://" + url

        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            if domain in ONLINE_JUDGE_DOMAINS:
                online_judge_urls.append(url)
                online_judge_sites.append(ONLINE_JUDGE_DOMAINS[domain])
        except:
            continue

    return {
        "all_urls": urls,
        "online_judge_urls": online_judge_urls,
        "online_judge_sites": online_judge_sites,
    }


# 편의 함수들
def crawl_problems_from_text(text: str, headless: bool = True) -> List[ProblemInfo]:
    """텍스트에서 온라인 저지 URL을 찾아 크롤링"""
    url_info = extract_online_judge_urls(text)
    urls = url_info["online_judge_urls"]

    if not urls:
        print("❌ 텍스트에서 온라인 저지 URL을 찾을 수 없습니다.")
        return []

    print(f"🎯 {len(urls)}개의 온라인 저지 URL 발견")

    results = []
    with MultiSiteSeleniumCrawler(headless=headless) as crawler:
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 크롤링 중...")
            problem = crawler.crawl_problem(url)
            results.append(problem)

            if problem.success:
                print(f"✅ 성공: {problem.site} - {problem.title}")
            else:
                print(f"❌ 실패: {problem.error_message}")

            # 다음 요청 전 잠시 대기 (서버 부하 방지)
            if i < len(urls):
                time.sleep(2)

    return results


def print_problem_details(problems: List[ProblemInfo]):
    """문제 정보들을 상세히 출력"""
    if not problems:
        print("📝 크롤링된 문제가 없습니다.")
        return

    print(f"\n{'=' * 80}")
    print(f"🎯 총 {len(problems)}개 문제 크롤링 결과")
    print(f"{'=' * 80}")

    # 통계 계산
    success_count = sum(1 for p in problems if p.success)
    site_stats = {}

    for problem in problems:
        site_stats[problem.site] = site_stats.get(problem.site, 0) + 1

    print(f"📊 성공: {success_count}개 | 실패: {len(problems) - success_count}개")
    print(f"📈 사이트별 통계: {dict(site_stats)}")

    # 개별 문제 상세 정보
    for i, problem in enumerate(problems, 1):
        print(f"\n{'─' * 60}")
        print(f"🔢 문제 {i}: {problem.site} - {problem.problem_id}")
        print(f"📝 제목: {problem.title}")
        print(f"🌐 URL: {problem.url}")

        if problem.success:
            if problem.difficulty:
                print(f"⚡ 난이도: {problem.difficulty}")

            if problem.time_limit:
                print(f"⏰ 시간 제한: {problem.time_limit}")

            if problem.memory_limit:
                print(f"💾 메모리 제한: {problem.memory_limit}")

            if problem.description:
                desc = (
                    problem.description[:200] + "..."
                    if len(problem.description) > 200
                    else problem.description
                )
                print(f"📖 설명: {desc}")

            if problem.examples:
                print(f"📋 예제 개수: {len(problem.examples)}개")
                # 첫 번째 예제만 출력
                if problem.examples:
                    ex = problem.examples[0]
                    print(
                        f"   입력: {ex['input'][:50]}{'...' if len(ex['input']) > 50 else ''}"
                    )
                    print(
                        f"   출력: {ex['output'][:50]}{'...' if len(ex['output']) > 50 else ''}"
                    )
        else:
            print(f"❌ 오류: {problem.error_message}")


def format_problem_for_llm(
    problem: ProblemInfo,
    include_examples: bool = True,
    max_description_length: int = 1000,
) -> str:
    """
    ProblemInfo를 LLM이 읽기 쉬운 형태로 변환하는 함수

    Args:
        problem: ProblemInfo 객체
        include_examples: 예제 입출력 포함 여부
        max_description_length: 설명 최대 길이 (너무 길면 잘림)

    Returns:
        str: LLM 친화적인 형태로 포맷된 문자열
    """

    if not problem.success:
        return f"""
❌ PROBLEM EXTRACTION FAILED
Site: {problem.site}
URL: {problem.url}
Error: {problem.error_message}
"""

    lines = []

    # 헤더 섹션
    header = "📚 PROBLEM INFORMATION"
    lines.append(header)
    lines.append("=" * len(header))
    lines.append("")

    # 기본 정보
    lines.append(f"🌐 Site: {problem.site}")
    lines.append(f"🔢 Problem ID: {problem.problem_id}")
    lines.append(f"📝 Title: {problem.title}")

    if problem.difficulty:
        lines.append(f"⚡ Difficulty: {problem.difficulty}")

    if problem.url:
        lines.append(f"🔗 URL: {problem.url}")

    lines.append("")

    # 제한 사항
    if problem.time_limit or problem.memory_limit:
        lines.append("⏱️ CONSTRAINTS")
        lines.append("-" * 12)

        if problem.time_limit:
            lines.append(f"• Time Limit: {problem.time_limit}")

        if problem.memory_limit:
            lines.append(f"• Memory Limit: {problem.memory_limit}")

        lines.append("")

    # 태그
    if problem.tags:
        lines.append("🏷️ TAGS")
        lines.append("-" * 6)
        tags_str = ", ".join(problem.tags)
        lines.append(f"• {tags_str}")
        lines.append("")

    # 문제 설명
    if problem.description:
        lines.append("📖 PROBLEM DESCRIPTION")
        lines.append("-" * 20)

        # 설명이 너무 길면 자르기
        description = problem.description
        if len(description) > max_description_length:
            description = description[:max_description_length] + "... [truncated]"

        # 긴 설명을 적절히 줄바꿈
        lines.append(description)
        lines.append("")

    # 입력 형식
    if problem.input_format:
        lines.append("📥 INPUT FORMAT")
        lines.append("-" * 14)
        lines.append(problem.input_format)
        lines.append("")

    # 출력 형식
    if problem.output_format:
        lines.append("📤 OUTPUT FORMAT")
        lines.append("-" * 15)
        lines.append(problem.output_format)
        lines.append("")

    # 예제
    if include_examples and problem.examples:
        lines.append("💡 EXAMPLES")
        lines.append("-" * 10)

        for i, example in enumerate(problem.examples, 1):
            lines.append(f"Example {i}:")
            lines.append("  Input:")
            # 입력이 여러 줄인 경우 들여쓰기
            input_lines = example.get("input", "").strip().split("\n")
            for input_line in input_lines:
                lines.append(f"    {input_line}")

            lines.append("  Output:")
            # 출력이 여러 줄인 경우 들여쓰기
            output_lines = example.get("output", "").strip().split("\n")
            for output_line in output_lines:
                lines.append(f"    {output_line}")

            lines.append("")

    return "\n".join(lines)


# 테스트 및 사용 예시
if __name__ == "__main__":
    # 테스트 문장 - 5개 사이트 모두 포함
    test_text = """
    5대 온라인 저지 사이트 문제들을 테스트해보겠습니다:
    
    1. Baekjoon: https://www.acmicpc.net/problem/1000
    2. Programmers: https://programmers.co.kr/learn/courses/30/lessons/42576
    3. LeetCode: https://leetcode.com/problems/two-sum/
    4. Codeforces: https://codeforces.com/contest/1/problem/A
    5. HackerRank: https://www.hackerrank.com/challenges/solve-me-first/problem
    """

    print("🚀 셀레니움 기반 5대 온라인 저지 크롤러 테스트 시작!")
    print(
        f"지원 사이트: {', '.join(MultiSiteSeleniumCrawler.SUPPORTED_SITES.values())}"
    )

    # 크롤링 실행
    problems = crawl_problems_from_text(test_text, headless=True)

    # 결과 출력
    print_problem_details(problems)

    # 성공한 문제들만 따로 출력
    successful_problems = [p for p in problems if p.success]
    if successful_problems:
        print(f"\n🎉 성공적으로 크롤링된 {len(successful_problems)}개 문제:")
        for problem in successful_problems:
            print(f"  ✅ {problem.site}: {problem.title}")

    print("\n💡 사용법:")
    print("1. 텍스트에서 자동 추출: crawl_problems_from_text('백준 1000번 문제...')")
    print("2. 개별 URL 크롤링:")
    print("   with MultiSiteSeleniumCrawler() as crawler:")
    print(
        "       problem = crawler.crawl_problem('https://www.acmicpc.net/problem/1000')"
    )

    print("\n📋 필요한 설치:")
    print("pip install selenium beautifulsoup4")
    print("Chrome 브라우저 및 chromedriver 설치 필요")

    print("\n⚠️ 주의사항:")
    print("- 각 사이트의 이용약관을 확인하세요")
    print("- 과도한 요청으로 인한 IP 차단에 주의하세요")
    print("- 일부 사이트는 로그인이 필요할 수 있습니다")

# 추가 유틸리티 함수들


def crawl_single_problem(
    url: str, headless: bool = True, show_details: bool = True
) -> ProblemInfo:
    """단일 문제 URL 크롤링"""
    with MultiSiteSeleniumCrawler(headless=headless) as crawler:
        problem = crawler.crawl_problem(url)

        if show_details:
            print_problem_details([problem])

        return problem


def get_supported_sites() -> List[str]:
    """지원하는 사이트 목록 반환"""
    return list(MultiSiteSeleniumCrawler.SUPPORTED_SITES.values())


def batch_crawl_urls(
    urls: List[str], headless: bool = True, delay: int = 2
) -> List[ProblemInfo]:
    """URL 리스트를 배치로 크롤링"""
    results = []

    print(f"🎯 {len(urls)}개 URL 배치 크롤링 시작")

    with MultiSiteSeleniumCrawler(headless=headless) as crawler:
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")

            problem = crawler.crawl_problem(url)
            results.append(problem)

            if problem.success:
                print(f"✅ {problem.site}: {problem.title}")
            else:
                print(f"❌ 실패: {problem.error_message}")

            # 마지막이 아니면 대기
            if i < len(urls):
                time.sleep(delay)

    return results


def save_problems_to_json(problems: List[ProblemInfo], filename: str = "problems.json"):
    """문제 정보들을 JSON 파일로 저장"""
    import json
    from dataclasses import asdict

    problems_data = []
    for problem in problems:
        problem_dict = asdict(problem)
        problems_data.append(problem_dict)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(problems_data, f, ensure_ascii=False, indent=2)

    print(f"💾 {len(problems)}개 문제 정보가 {filename}에 저장되었습니다.")


def load_problems_from_json(filename: str = "problems.json") -> List[ProblemInfo]:
    """JSON 파일에서 문제 정보들을 로드"""
    import json

    try:
        with open(filename, "r", encoding="utf-8") as f:
            problems_data = json.load(f)

        problems = []
        for problem_dict in problems_data:
            problem = ProblemInfo(**problem_dict)
            problems.append(problem)

        print(f"📁 {filename}에서 {len(problems)}개 문제 정보를 로드했습니다.")
        return problems

    except FileNotFoundError:
        print(f"❌ {filename} 파일을 찾을 수 없습니다.")
        return []
    except Exception as e:
        print(f"❌ 파일 로딩 중 오류: {e}")
        return []


# 성능 테스트 함수
def performance_test():
    """크롤러 성능 테스트"""
    test_urls = [
        "https://www.acmicpc.net/problem/1000",  # 백준 - 가장 쉬운 문제
        "https://programmers.co.kr/learn/courses/30/lessons/42576",  # 프로그래머스
        "https://leetcode.com/problems/two-sum/",  # 리트코드
    ]

    print("⚡ 성능 테스트 시작...")
    start_time = time.time()

    problems = batch_crawl_urls(test_urls, headless=True, delay=1)

    end_time = time.time()
    total_time = end_time - start_time

    success_count = sum(1 for p in problems if p.success)

    print("\n📊 성능 테스트 결과:")
    print(f"   총 소요 시간: {total_time:.2f}초")
    print(f"   평균 처리 시간: {total_time / len(test_urls):.2f}초/문제")
    print(
        f"   성공률: {success_count}/{len(test_urls)} ({success_count / len(test_urls) * 100:.1f}%)"
    )

    return problems


# 에러 분석 함수
def analyze_errors(problems: List[ProblemInfo]):
    """크롤링 에러 분석"""
    failed_problems = [p for p in problems if not p.success]

    if not failed_problems:
        print("🎉 모든 문제가 성공적으로 크롤링되었습니다!")
        return

    print(f"\n🔍 에러 분석 ({len(failed_problems)}개 실패):")

    error_types = {}
    site_errors = {}

    for problem in failed_problems:
        # 에러 타입별 분류
        error_msg = problem.error_message or "Unknown error"
        error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg
        error_types[error_type] = error_types.get(error_type, 0) + 1

        # 사이트별 에러
        site_errors[problem.site] = site_errors.get(problem.site, 0) + 1

    print("📈 에러 타입별 통계:")
    for error_type, count in error_types.items():
        print(f"   {error_type}: {count}개")

    print("🌐 사이트별 실패 통계:")
    for site, count in site_errors.items():
        print(f"   {site}: {count}개")

    print("\n💡 해결 방안:")
    print("   - JavaScript 로딩 시간 부족: time.sleep() 증가")
    print("   - 요소를 찾을 수 없음: 사이트 구조 변경 확인")
    print("   - 로그인 필요: 인증 기능 추가 고려")
    print("   - 네트워크 오류: 재시도 로직 구현")


# 사이트별 성능 비교
def compare_site_performance():
    """사이트별 크롤링 성능 비교"""
    test_urls = {
        "Baekjoon": "https://www.acmicpc.net/problem/1000",
        "Programmers": "https://programmers.co.kr/learn/courses/30/lessons/42576",
        "LeetCode": "https://leetcode.com/problems/two-sum/",
        "Codeforces": "https://codeforces.com/contest/1/problem/A",
        "HackerRank": "https://www.hackerrank.com/challenges/solve-me-first/problem",
    }

    results = {}

    print("🏆 사이트별 성능 비교 테스트")
    print("-" * 50)

    with MultiSiteSeleniumCrawler(headless=True) as crawler:
        for site_name, url in test_urls.items():
            print(f"\n🔍 {site_name} 테스트 중...")

            start_time = time.time()
            problem = crawler.crawl_problem(url)
            end_time = time.time()

            duration = end_time - start_time
            results[site_name] = {
                "duration": duration,
                "success": problem.success,
                "title": problem.title if problem.success else "실패",
                "problem": problem,
            }

            status = "✅" if problem.success else "❌"
            print(
                f"{status} {site_name}: {duration:.2f}초 - {results[site_name]['title']}"
            )

            time.sleep(1)  # 서버 부하 방지

    # 결과 정렬 (성공한 것들만, 속도 순)
    successful_results = {k: v for k, v in results.items() if v["success"]}
    sorted_results = sorted(successful_results.items(), key=lambda x: x[1]["duration"])

    print("\n🥇 성능 순위 (성공한 사이트만):")
    for i, (site_name, result) in enumerate(sorted_results, 1):
        print(f"   {i}위. {site_name}: {result['duration']:.2f}초")

    return results
