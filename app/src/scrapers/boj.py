from bs4 import BeautifulSoup

from .base import BaseScraper
from .models import ProblemData, TestCase


class BOJScraper(BaseScraper):
    BASE_URL = "https://www.acmicpc.net/problem"

    async def get_problem(self, problem_id: str) -> ProblemData:
        target_url = f"{self.BASE_URL}/{problem_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        response = await self.client.get(target_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title_elem = soup.select_one("#problem_title")
        if not title_elem:
            raise ValueError("백준 문제 페이지를 파싱할 수 없습니다.")
        title = title_elem.get_text(strip=True)

        # Problem Info Table
        info_table = soup.select_one("#problem-info")
        time_limit = "N/A"
        memory_limit = "N/A"

        if info_table:
            tds = info_table.select("td")
            if len(tds) >= 2:
                time_limit = tds[0].get_text(strip=True)
                memory_limit = tds[1].get_text(strip=True)

        # Description & IO
        desc_elem = soup.select_one("#problem_description")
        input_elem = soup.select_one("#problem_input")
        output_elem = soup.select_one("#problem_output")

        description = desc_elem.get_text(strip=True) if desc_elem else ""
        input_desc = input_elem.get_text(strip=True) if input_elem else ""
        output_desc = output_elem.get_text(strip=True) if output_elem else ""

        # Test Cases
        test_cases = []
        idx = 1
        while True:
            input_node = soup.select_one(f"#sample-input-{idx}")
            output_node = soup.select_one(f"#sample-output-{idx}")

            if not input_node or not output_node:
                break

            test_cases.append(
                TestCase(input=input_node.get_text(), output=output_node.get_text())
            )
            idx += 1

        # Tags
        tags = []
        tags_div = soup.select_one("#problem_tags")
        if tags_div:
            for tag_link in tags_div.select("li a"):
                tags.append(tag_link.get_text(strip=True))

        return ProblemData(
            platform="BOJ",
            problem_id=problem_id,
            url=target_url,
            title=title,
            description=description,
            input_desc=input_desc,
            output_desc=output_desc,
            time_limit=time_limit,
            memory_limit=memory_limit,
            difficulty=None,
            tags=tags,
            test_cases=test_cases,
        )
