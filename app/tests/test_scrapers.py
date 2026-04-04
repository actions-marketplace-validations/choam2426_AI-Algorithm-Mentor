from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio

from src.scrapers.boj import BOJScraper
from src.scrapers.models import ProblemData, TestCase


class TestBOJScraperParsing:
    """Tests for BOJ scraper HTML parsing logic.

    These tests mock the HTTP layer and verify that get_problem
    correctly extracts structured data from raw HTML.
    """

    @pytest_asyncio.fixture
    async def scraper_with_mock_response(self, boj_problem_html):
        """Create a BOJScraper with a mocked _fetch_with_fallback."""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        scraper = BOJScraper(client=mock_client)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = boj_problem_html
        mock_response.status_code = 200

        scraper._fetch_with_fallback = AsyncMock(return_value=mock_response)
        return scraper

    @pytest.mark.asyncio
    async def test_parses_title(self, scraper_with_mock_response):
        result = await scraper_with_mock_response.get_problem("1000")

        assert isinstance(result, ProblemData)
        assert result.title == "A+B"

    @pytest.mark.asyncio
    async def test_parses_metadata(self, scraper_with_mock_response):
        result = await scraper_with_mock_response.get_problem("1000")

        assert result.platform == "BOJ"
        assert result.problem_id == "1000"
        assert result.url == "https://www.acmicpc.net/problem/1000"

    @pytest.mark.asyncio
    async def test_parses_constraints(self, scraper_with_mock_response):
        result = await scraper_with_mock_response.get_problem("1000")

        assert result.time_limit == "2 초"
        assert result.memory_limit == "128 MB"

    @pytest.mark.asyncio
    async def test_parses_description(self, scraper_with_mock_response):
        result = await scraper_with_mock_response.get_problem("1000")

        assert "A+B를 출력" in result.description
        assert result.input_desc != ""
        assert result.output_desc != ""

    @pytest.mark.asyncio
    async def test_parses_test_cases(self, scraper_with_mock_response):
        result = await scraper_with_mock_response.get_problem("1000")

        assert len(result.test_cases) == 2
        assert isinstance(result.test_cases[0], TestCase)
        assert "1 2" in result.test_cases[0].input
        assert "3" in result.test_cases[0].output
        assert "3 4" in result.test_cases[1].input
        assert "7" in result.test_cases[1].output

    @pytest.mark.asyncio
    async def test_parses_tags(self, scraper_with_mock_response):
        result = await scraper_with_mock_response.get_problem("1000")

        assert "수학" in result.tags
        assert "구현" in result.tags

    @pytest.mark.asyncio
    async def test_missing_title_raises(self):
        """Page without #problem_title raises ValueError."""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        scraper = BOJScraper(client=mock_client)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body><p>No title here</p></body></html>"
        mock_response.status_code = 200
        scraper._fetch_with_fallback = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="파싱할 수 없습니다"):
            await scraper.get_problem("9999")

    @pytest.mark.asyncio
    async def test_missing_optional_sections(self):
        """Page with title but missing description/input/output returns empty strings."""
        html = """
<html><body>
<span id="problem_title">Minimal Problem</span>
</body></html>
"""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        scraper = BOJScraper(client=mock_client)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = html
        mock_response.status_code = 200
        scraper._fetch_with_fallback = AsyncMock(return_value=mock_response)

        result = await scraper.get_problem("1")

        assert result.description == ""
        assert result.input_desc == ""
        assert result.output_desc == ""
        assert result.time_limit == "N/A"
        assert result.memory_limit == "N/A"
        assert result.test_cases == []
        assert result.tags == []
