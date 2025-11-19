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
        # Note: specific class might vary, but usually .guide-section-description
        content_div = soup.select_one(".guide-section-description")
        if not content_div:
            # Sometimes the structure is different or loaded dynamically.
            # If completely dynamic, static parsing fails.
            # Programmers usually renders content server-side for these pages, let's hope.
            # If it fails, we might return empty/error.
            content_div = soup.select_one(
                "#tour-main-step"
            )  # Another possible container

        description = ""
        # input_desc = ""
        # output_desc = ""
        # constraints = []
        test_cases = []

        if content_div:
            # Simple text extraction for description
            # We can try to split by headers if possible.
            # Common headers: "문제 설명", "제한사항", "입출력 예"

            text = content_div.get_text("\n", strip=True)

            # Naive parsing by sections
            # This is heuristic and might break.

            # Extract Constraints (Time/Memory usually not explicitly separated fields in Programmers,
            # they are just text in "Limit" section)
            # We will put "Limit" section text into input_desc/constraints.

            # Extracting Test Cases from Table
            tables = content_div.select("table")
            if tables:
                # The last table is OFTEN the IO example.
                io_table = tables[-1]
                headers = [
                    th.get_text(strip=True) for th in io_table.select("thead th")
                ]
                # Usually: ["parameter1", "parameter2", ..., "return"]

                rows = io_table.select("tbody tr")
                for row in rows:
                    cols = [td.get_text(strip=True) for td in row.select("td")]
                    if len(cols) >= 2:
                        # Last col is output, others are input joined
                        inp = ", ".join(
                            f"{h}={v}" for h, v in zip(headers[:-1], cols[:-1])
                        )
                        out = cols[-1]
                        test_cases.append(TestCase(input=inp, output=out))

            description = text  # Placeholder for full text

        return ProblemData(
            platform="Programmers",
            problem_id=problem_id,
            url=url,
            title=title,
            description=description,  # Contains everything for now
            input_desc="See description (Programmers usually mixes these)",
            output_desc="See description",
            time_limit=None,
            memory_limit=None,
            difficulty=None,
            tags=[],
            test_cases=test_cases,
        )
