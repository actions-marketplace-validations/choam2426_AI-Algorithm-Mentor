import httpx

from .base import BaseScraper
from .boj import BOJScraper
from .leetcode import LeetCodeScraper
from .programmers import ProgrammersScraper


def get_scraper(platform: str, client: httpx.AsyncClient) -> BaseScraper:
    if platform == "BOJ":
        return BOJScraper(client)
    elif platform == "LeetCode":
        return LeetCodeScraper(client)
    elif platform == "Programmers":
        return ProgrammersScraper(client)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
