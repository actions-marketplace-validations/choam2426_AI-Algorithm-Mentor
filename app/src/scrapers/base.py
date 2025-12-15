import re
from abc import ABC, abstractmethod

import httpx
from bs4 import NavigableString, Tag

from .models import ProblemData

# Block-level elements that should have newlines
BLOCK_ELEMENTS = {
    "p",
    "div",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "hr",
    "tr",
}


class BaseScraper(ABC):
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def _table_to_markdown(self, table: Tag) -> str:
        """Convert HTML table to Markdown format."""
        rows = []

        # Extract headers
        headers = []
        thead = table.select_one("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.select("th")]

        if headers:
            rows.append("| " + " | ".join(headers) + " |")
            rows.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Extract body rows
        tbody = table.select_one("tbody") or table
        for tr in tbody.select("tr"):
            cells = [td.get_text(strip=True) for td in tr.select("td")]
            if cells:
                rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows)

    def _extract_text(self, element: Tag) -> str:
        """
        Extract text from HTML element with proper handling of
        inline vs block elements.
        """
        parts = []

        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child)
                # Normalize whitespace but preserve some spacing
                text = re.sub(r"\s+", " ", text)
                parts.append(text)
            elif isinstance(child, Tag):
                if child.name == "table":
                    # Convert table to markdown
                    parts.append("\n\n" + self._table_to_markdown(child) + "\n\n")
                elif child.name == "br":
                    parts.append("\n")
                elif child.name in BLOCK_ELEMENTS:
                    # Block elements get newlines
                    inner_text = self._extract_text(child)
                    parts.append("\n" + inner_text.strip() + "\n")
                elif child.name == "code":
                    # Inline code - wrap with backticks
                    parts.append("`" + child.get_text() + "`")
                else:
                    # Inline elements - just extract text
                    parts.append(self._extract_text(child))

        result = "".join(parts)
        # Clean up excessive newlines
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    @abstractmethod
    async def get_problem(self, problem_id: str) -> ProblemData:
        """
        Fetches and parses problem data from the online judge.

        Args:
            problem_id: The identifier for the problem on the platform.

        Returns:
            ProblemData object containing parsed information.
        """
        pass
