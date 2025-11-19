import json

from bs4 import BeautifulSoup

from .base import BaseScraper
from .models import ProblemData, TestCase


class LeetCodeScraper(BaseScraper):
    BASE_URL = "https://leetcode.com/problems"
    GRAPHQL_URL = "https://leetcode.com/graphql"

    async def get_problem(self, problem_id: str) -> ProblemData:
        # problem_id here is expected to be the titleSlug (e.g., "two-sum")

        query = """
        query getQuestionDetail($titleSlug: String!) {
          question(titleSlug: $titleSlug) {
            questionId
            title
            content
            difficulty
            topicTags {
              name
            }
            sampleTestCase
            metaData
          }
        }
        """

        variables = {"titleSlug": problem_id}
        payload = {
            "query": query,
            "variables": variables,
            "operationName": "getQuestionDetail",
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.BASE_URL}/{problem_id}/",
        }

        response = await self.client.post(
            self.GRAPHQL_URL, json=payload, headers=headers
        )
        response.raise_for_status()

        data = response.json()
        if "errors" in data:
            raise ValueError(f"GraphQL Error: {data['errors']}")

        question = data.get("data", {}).get("question")
        if not question:
            raise ValueError(f"Problem not found: {problem_id}")

        # Parse content
        soup = BeautifulSoup(question["content"], "html.parser")
        description = soup.get_text("\n", strip=True)

        # Extract test cases from content (Example sections)
        test_cases = []
        # LeetCode examples are usually in <pre> tags or <div class="example-block">
        # This is tricky as format changes.
        # We'll just store the raw sampleTestCase as one input if parsing fails,
        # or try to parse the text representation in description.

        # Heuristic: Find text "Input:" and "Output:"
        # This is hard to robustly implement without complex regex.
        # For now, we will use the provided sampleTestCase as a single input case (without output known)
        # or leave it empty if we want strict Input/Output pairs.
        # LeetCode often puts Input/Output in <pre> text.

        # Let's try to find <pre> tags
        pre_blocks = soup.find_all("pre")
        for pre in pre_blocks:
            text = pre.get_text()
            if "Input:" in text and "Output:" in text:
                # Simple parsing
                try:
                    input_part = text.split("Input:")[1].split("Output:")[0].strip()
                    output_part = (
                        text.split("Output:")[1].split("Explanation:")[0].strip()
                    )  # Remove Explanation if present
                    test_cases.append(TestCase(input=input_part, output=output_part))
                except:
                    pass

        # Metadata
        meta = json.loads(question.get("metaData", "{}"))
        # metaData often contains params structure but not limits.

        # Constraints are often in the content text at the bottom
        # e.g. "Constraints:" section.

        tags = [t["name"] for t in question.get("topicTags", [])]

        return ProblemData(
            platform="LeetCode",
            problem_id=question["questionId"],
            url=f"{self.BASE_URL}/{problem_id}/",
            title=question["title"],
            description=description,
            input_desc="See description",
            output_desc="See description",
            time_limit=None,  # LeetCode doesn't expose fixed time limit per problem easily
            memory_limit=None,
            difficulty=question["difficulty"],
            tags=tags,
            test_cases=test_cases,
        )
