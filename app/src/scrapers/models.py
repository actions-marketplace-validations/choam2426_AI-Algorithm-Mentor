from typing import List, Optional

from pydantic import BaseModel


class TestCase(BaseModel):
    input: str
    output: str


class ProblemData(BaseModel):
    # Metadata
    platform: str
    problem_id: str
    url: str

    # Problem Info
    title: str
    description: str
    input_desc: str
    output_desc: str

    # Constraints
    time_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    difficulty: Optional[str] = None
    tags: List[str] = []

    # solved.ac enrichment (BOJ only)
    solved_ac_level: Optional[int] = None

    # Test Cases
    test_cases: List[TestCase] = []
