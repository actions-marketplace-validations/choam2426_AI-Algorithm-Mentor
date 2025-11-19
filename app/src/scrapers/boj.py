from bs4 import BeautifulSoup

from .base import BaseScraper
from .models import ProblemData, TestCase


class BOJScraper(BaseScraper):
    BASE_URL = "https://www.acmicpc.net/problem"

    async def get_problem(self, problem_id: str) -> ProblemData:
        url = f"{self.BASE_URL}/{problem_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = await self.client.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Meta & Constraints
        title = soup.select_one("#problem_title").get_text(strip=True)

        # Problem Info Table
        info_table = soup.select_one("#problem-info")
        time_limit = "N/A"
        memory_limit = "N/A"

        if info_table:
            # Usually: Time Limit | Memory Limit | ...
            # td:nth-child(1) -> Time, td:nth-child(2) -> Memory
            tds = info_table.select("td")
            if len(tds) >= 2:
                time_limit = tds[0].get_text(strip=True)
                memory_limit = tds[1].get_text(strip=True)

        # Description & IO
        description = soup.select_one("#problem_description").get_text(strip=True)
        input_desc = soup.select_one("#problem_input").get_text(strip=True)
        output_desc = soup.select_one("#problem_output").get_text(strip=True)

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

        # Tags (Static parsing might be limited if hidden behind JS)
        # BOJ structure: div#problem_tags > ul > li > a
        tags = []
        tags_div = soup.select_one("#problem_tags")
        if tags_div:
            for tag_link in tags_div.select("li a"):
                tags.append(tag_link.get_text(strip=True))

        return ProblemData(
            platform="BOJ",
            problem_id=problem_id,
            url=url,
            title=title,
            description=description,
            input_desc=input_desc,
            output_desc=output_desc,
            time_limit=time_limit,
            memory_limit=memory_limit,
            difficulty=None,  # Hard to get from problem page directly without login/settings sometimes
            tags=tags,
            test_cases=test_cases,
        )
