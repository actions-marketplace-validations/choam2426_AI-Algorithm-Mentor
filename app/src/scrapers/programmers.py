from bs4 import BeautifulSoup

from .base import BaseScraper
from .models import ProblemData, TestCase


class ProgrammersScraper(BaseScraper):
    BASE_URL = "https://school.programmers.co.kr/learn/courses/30/lessons"

    async def get_problem(self, problem_id: str) -> ProblemData:
        url = f"{self.BASE_URL}/{problem_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = await self.client.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Title usually in a meta tag or li.algorithm-title which might be dynamic.
        # Fallback to page title
        page_title = soup.title.string if soup.title else "Unknown Problem"
        title = page_title.split("|")[0].strip()

        # Content container
        content_div = soup.select_one(".guide-section-description")
        if not content_div:
            content_div = soup.select_one("#tour-main-step")

        description = ""
        test_cases = []

        if content_div:
            # Extract description with proper formatting
            description = self._extract_text(content_div)

            # Extracting Test Cases from Table
            tables = content_div.select("table")
            if tables:
                # The last table is OFTEN the IO example.
                io_table = tables[-1]
                table_headers = [
                    th.get_text(strip=True) for th in io_table.select("thead th")
                ]

                rows = io_table.select("tbody tr")
                for row in rows:
                    cols = [td.get_text(strip=True) for td in row.select("td")]
                    if len(cols) >= 2:
                        inp = ", ".join(
                            f"{h}={v}" for h, v in zip(table_headers[:-1], cols[:-1])
                        )
                        out = cols[-1]
                        test_cases.append(TestCase(input=inp, output=out))

        return ProblemData(
            platform="Programmers",
            problem_id=problem_id,
            url=url,
            title=title,
            description=description,
            input_desc="See description",
            output_desc="See description",
            time_limit=None,
            memory_limit=None,
            difficulty=None,
            tags=[],
            test_cases=test_cases,
        )
