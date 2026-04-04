from bs4 import BeautifulSoup, Tag

from .base import BaseScraper
from .models import ProblemData, TestCase


class CodeforcesScraper(BaseScraper):
    BASE_URL = "https://codeforces.com"

    async def get_problem(self, problem_id: str) -> ProblemData:
        """
        Fetches and parses a Codeforces problem.

        Args:
            problem_id: Format "{contestId}/{index}", e.g. "1/A" or "1998/A".

        Returns:
            ProblemData with title, description, test cases, etc.
        """
        parts = problem_id.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid Codeforces problem_id format: '{problem_id}'. "
                "Expected '{contestId}/{index}', e.g. '1/A'."
            )

        contest_id, index = parts[0], parts[1]
        url = f"{self.BASE_URL}/problemset/problem/{contest_id}/{index}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = await self.client.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        problem_statement = soup.select_one("div.problem-statement")
        if not problem_statement:
            raise ValueError(
                f"Could not parse Codeforces problem page for '{problem_id}'."
            )

        # Title: inside div.problem-statement > div.header > div.title
        title = self._parse_title(problem_statement)

        # Time and memory limits from div.header
        time_limit = self._parse_limit(problem_statement, "time-limit")
        memory_limit = self._parse_limit(problem_statement, "memory-limit")

        # Description, input/output descriptions
        description, input_desc, output_desc = self._parse_sections(problem_statement)

        # Test cases from div.sample-test
        test_cases = self._parse_test_cases(problem_statement)

        # Tags
        tags = self._parse_tags(soup)

        # Difficulty (rating) from the sidebar span.tag-box[title="Difficulty"]
        difficulty = self._parse_difficulty(soup)

        return ProblemData(
            platform="Codeforces",
            problem_id=problem_id,
            url=url,
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

    def _parse_title(self, problem_statement: Tag) -> str:
        header = problem_statement.select_one("div.header")
        if not header:
            raise ValueError("Problem header not found.")
        title_elem = header.select_one("div.title")
        if not title_elem:
            raise ValueError("Problem title not found.")
        return title_elem.get_text(strip=True)

    def _parse_limit(self, problem_statement: Tag, css_class: str) -> str | None:
        header = problem_statement.select_one("div.header")
        if not header:
            return None
        limit_div = header.select_one(f"div.{css_class}")
        if not limit_div:
            return None
        # The div contains a child div.property-title ("time limit per test")
        # followed by the actual value text. We extract only the value portion.
        text = limit_div.get_text(strip=True)
        # Remove the property title prefix if present
        property_title = limit_div.select_one("div.property-title")
        if property_title:
            prefix = property_title.get_text(strip=True)
            text = text.removeprefix(prefix).strip()
        return text if text else None

    def _parse_sections(
        self, problem_statement: Tag
    ) -> tuple[str, str, str]:
        """
        Parse the main description, input specification, and output specification.

        Codeforces problem-statement layout (children of div.problem-statement):
          - div.header (already handled)
          - bare div (no class) = main description
          - div.input-specification
          - div.output-specification
          - div.sample-tests (handled separately)
          - div.note (optional)
        """
        description = ""
        input_desc = ""
        output_desc = ""

        # Main description: the first bare <div> child that has no class attribute
        # after the header div.
        header_seen = False
        for child in problem_statement.children:
            if not isinstance(child, Tag):
                continue
            if child.get("class") and "header" in child.get("class", []):
                header_seen = True
                continue
            if header_seen and not child.get("class"):
                description = self._extract_text(child)
                break

        input_spec = problem_statement.select_one("div.input-specification")
        if input_spec:
            input_desc = self._extract_text(input_spec)

        output_spec = problem_statement.select_one("div.output-specification")
        if output_spec:
            output_desc = self._extract_text(output_spec)

        return description, input_desc, output_desc

    def _parse_test_cases(self, problem_statement: Tag) -> list[TestCase]:
        test_cases: list[TestCase] = []
        sample_test = problem_statement.select_one("div.sample-test")
        if not sample_test:
            return test_cases

        inputs = sample_test.select("div.input pre")
        outputs = sample_test.select("div.output pre")

        for inp, out in zip(inputs, outputs):
            # Codeforces uses <br> inside <pre> for line breaks in some cases.
            # get_text() handles that, but we ensure newlines from <br>.
            input_text = self._pre_text(inp)
            output_text = self._pre_text(out)
            test_cases.append(TestCase(input=input_text, output=output_text))

        return test_cases

    def _pre_text(self, pre_tag: Tag) -> str:
        """Extract text from a <pre> tag, converting <br> to newlines."""
        # Replace <br> with newline before extracting text
        for br in pre_tag.find_all("br"):
            br.replace_with("\n")
        return pre_tag.get_text()

    def _parse_tags(self, soup: BeautifulSoup) -> list[str]:
        tags: list[str] = []
        # Tags are in the sidebar: span.tag-box elements inside div.roundbox.sidebox
        # that are NOT the difficulty tag.
        tag_boxes = soup.select("span.tag-box")
        for tag_box in tag_boxes:
            title_attr = tag_box.get("title", "")
            if title_attr == "Difficulty":
                continue
            text = tag_box.get_text(strip=True)
            if text:
                tags.append(text)
        return tags

    def _parse_difficulty(self, soup: BeautifulSoup) -> str | None:
        # Difficulty rating in span.tag-box[title="Difficulty"]
        diff_tag = soup.select_one('span.tag-box[title="Difficulty"]')
        if diff_tag:
            text = diff_tag.get_text(strip=True)
            if text:
                return text
        return None
