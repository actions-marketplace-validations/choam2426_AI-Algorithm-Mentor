import re

from bs4 import BeautifulSoup

from ..logger import logger
from .base import BaseScraper
from .models import ProblemData, TestCase


class CodeforcesScraper(BaseScraper):
    BASE_URL = "https://codeforces.com"
    API_BASE_URL = "https://codeforces.com/api"

    def _parse_problem_id(self, problem_id: str) -> tuple[str, str]:
        """Parse a Codeforces problem identifier into (contest_id, index).

        Accepted formats:
          - "1920/A" or "1920/B1"
          - "1920A" or "1920B1"

        Returns:
            Tuple of (contest_id, index) e.g. ("1920", "A").

        Raises:
            ValueError: If the problem_id format is not recognised.
        """
        # Try slash-separated first: "1920/A"
        if "/" in problem_id:
            parts = problem_id.split("/", 1)
            if len(parts) == 2 and parts[0].isdigit() and parts[1]:
                return parts[0], parts[1].upper()

        # Try concatenated: "1920A", "1920B1"
        match = re.match(r"^(\d+)([A-Za-z]\d*)$", problem_id)
        if match:
            return match.group(1), match.group(2).upper()

        raise ValueError(
            f"Invalid Codeforces problem ID format: '{problem_id}'. "
            "Expected '<contest_id>/<index>' or '<contest_id><index>' "
            "(e.g. '1920/A' or '1920A')."
        )

    async def _fetch_html(self, contest_id: str, index: str) -> ProblemData:
        """Attempt to scrape problem data from the Codeforces website.

        Raises on any HTTP or parsing failure so the caller can fall through
        to the API fallback.
        """
        url = f"{self.BASE_URL}/contest/{contest_id}/problem/{index}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = await self.client.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Title -- e.g. "A. Satisfying Constraints"
        title_elem = soup.select_one(".title")
        if not title_elem:
            raise ValueError("Codeforces problem page could not be parsed (no title).")
        title = title_elem.get_text(strip=True)

        # Time / memory limits
        time_limit_elem = soup.select_one(".time-limit")
        time_limit = (
            time_limit_elem.get_text(strip=True).replace("time limit per test", "").strip()
            if time_limit_elem
            else None
        )
        memory_limit_elem = soup.select_one(".memory-limit")
        memory_limit = (
            memory_limit_elem.get_text(strip=True).replace("memory limit per test", "").strip()
            if memory_limit_elem
            else None
        )

        # Description
        problem_statement = soup.select_one(".problem-statement")
        description = ""
        if problem_statement:
            # The first div without a class inside .problem-statement is the description
            for div in problem_statement.find_all("div", recursive=False):
                cls = div.get("class")
                if not cls:
                    description = self._extract_text(div)
                    break

        # Input / Output descriptions
        input_spec = soup.select_one(".input-specification")
        input_desc = self._extract_text(input_spec) if input_spec else ""
        output_spec = soup.select_one(".output-specification")
        output_desc = self._extract_text(output_spec) if output_spec else ""

        # Test cases
        test_cases: list[TestCase] = []
        sample_tests = soup.select_one(".sample-tests")
        if sample_tests:
            inputs = sample_tests.select(".input pre")
            outputs = sample_tests.select(".output pre")
            for inp, out in zip(inputs, outputs):
                test_cases.append(
                    TestCase(input=inp.get_text(), output=out.get_text())
                )

        # Tags
        tags: list[str] = []
        for tag_elem in soup.select(".tag-box"):
            tag_text = tag_elem.get_text(strip=True)
            if tag_text and tag_text != "*special":
                tags.append(tag_text)

        # Difficulty (rating) -- shown as "*1400" in the tag area
        difficulty: str | None = None
        for tag_elem in soup.select(".tag-box"):
            tag_text = tag_elem.get_text(strip=True)
            if tag_text.startswith("*") and tag_text[1:].isdigit():
                difficulty = tag_text[1:]  # strip the leading '*'
                break

        return ProblemData(
            platform="Codeforces",
            problem_id=f"{contest_id}{index}",
            url=f"{self.BASE_URL}/contest/{contest_id}/problem/{index}",
            title=title,
            description=description,
            input_desc=input_desc,
            output_desc=output_desc,
            time_limit=time_limit,
            memory_limit=memory_limit,
            difficulty=difficulty,
            tags=tags,
            test_cases=test_cases,
        )

    async def _fetch_from_api(self, contest_id: str, index: str) -> ProblemData | None:
        """Fetch partial metadata from the Codeforces API.

        Uses contest.standings with count=1 to minimise payload.
        Returns a ProblemData with metadata only (no description/test cases),
        or None if the API call fails for any reason.
        """
        api_url = (
            f"{self.API_BASE_URL}/contest.standings"
            f"?contestId={contest_id}&from=1&count=1"
        )

        try:
            response = await self.client.get(api_url, timeout=15.0)
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "OK":
                logger.warning(
                    "Codeforces API returned non-OK status: %s",
                    data.get("status"),
                )
                return None

            problems = data.get("result", {}).get("problems", [])
            target = None
            for p in problems:
                if p.get("index", "").upper() == index.upper():
                    target = p
                    break

            if target is None:
                logger.warning(
                    "Codeforces API: problem index '%s' not found in contest %s.",
                    index,
                    contest_id,
                )
                return None

            name = target.get("name", "Unknown")
            rating = target.get("rating")
            tags = target.get("tags", [])

            return ProblemData(
                platform="Codeforces",
                problem_id=f"{contest_id}{index}",
                url=f"{self.BASE_URL}/contest/{contest_id}/problem/{index}",
                title=f"{index}. {name}",
                description="",
                input_desc="See problem page",
                output_desc="See problem page",
                time_limit=None,
                memory_limit=None,
                difficulty=str(rating) if rating is not None else None,
                tags=tags,
                test_cases=[],
            )

        except Exception as exc:
            logger.warning("Codeforces API fallback failed: %s", exc)
            return None

    async def get_problem(self, problem_id: str) -> ProblemData:
        """Fetch Codeforces problem data with HTML-first, API-fallback strategy.

        1. Try HTML scraping from codeforces.com.
        2. On failure, try the public Codeforces API for metadata.
        3. If both fail, raise the original exception so main.py can
           attempt the README.md fallback.
        """
        contest_id, index = self._parse_problem_id(problem_id)

        # --- Attempt 1: HTML scrape ---
        try:
            result = await self._fetch_html(contest_id, index)
            logger.info(
                "Codeforces HTML scrape succeeded for %s%s.", contest_id, index
            )
            return result
        except Exception as html_exc:
            logger.warning(
                "Codeforces HTML scrape failed for %s%s: %s",
                contest_id,
                index,
                html_exc,
            )

        # --- Attempt 2: API fallback ---
        logger.info(
            "Trying Codeforces API fallback for %s%s...", contest_id, index
        )
        api_result = await self._fetch_from_api(contest_id, index)
        if api_result is not None:
            logger.info(
                "Codeforces API fallback succeeded for %s%s "
                "(metadata only: title='%s', tags=%s, difficulty=%s).",
                contest_id,
                index,
                api_result.title,
                api_result.tags,
                api_result.difficulty,
            )
            return api_result

        # --- Both failed ---
        logger.error(
            "All Codeforces data sources failed for %s%s. "
            "If you use CFPusher, the README.md fallback may still work.",
            contest_id,
            index,
        )
        raise html_exc  # noqa: F821 -- guaranteed bound from the except block above
