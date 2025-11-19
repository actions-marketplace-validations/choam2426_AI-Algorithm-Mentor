from abc import ABC, abstractmethod

import httpx

from .models import ProblemData


class BaseScraper(ABC):
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

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
