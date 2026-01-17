import asyncio

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper
from .models import ProblemData, TestCase


class BOJScraper(BaseScraper):
    BASE_URL = "https://www.acmicpc.net/problem"

    async def _fetch_with_fallback(self, problem_id: str) -> httpx.Response:
        """
        최대 3번의 fallback 전략으로 BOJ 페이지를 가져옵니다.
        1) HTTP/1.1 + 기본 브라우저 헤더
        2) HTTP/2 + Client Hints 포함 헤더
        3) URL 변형: 끝 슬래시 추가, view=standard
        4) 그래도 실패 시 403 그대로 전달
        """
        base_url = f"{self.BASE_URL}/{problem_id}"

        # 전략 1: HTTP/1.1 + 기본 브라우저 헤더
        headers_v1 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        # 전략 2: HTTP/2 + Client Hints 포함 헤더
        headers_v2 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

        # 전략 3: URL 변형 + 동일 헤더
        url_variations = [
            f"{base_url}/",  # 끝 슬래시 추가
            f"{base_url}?view=standard",  # view=standard 파라미터
        ]

        strategies = [
            ("HTTP/1.1", base_url, headers_v1, False),
            ("HTTP/2 + Client Hints", base_url, headers_v2, True),
            ("URL 변형 (슬래시)", url_variations[0], headers_v2, True),
            ("URL 변형 (view=standard)", url_variations[1], headers_v2, True),
        ]

        last_response = None
        retry_delays = [0, 3.0, 5.0, 10.0]

        for i, (strategy_name, url, headers, use_http2) in enumerate(strategies):
            try:
                # 재시도 전 딜레이 (첫 시도 제외)
                if retry_delays[i] > 0:
                    await asyncio.sleep(retry_delays[i])

                if use_http2:
                    # HTTP/2 클라이언트 생성
                    async with httpx.AsyncClient(http2=True, timeout=30.0) as h2_client:
                        response = await h2_client.get(url, headers=headers)
                else:
                    response = await self.client.get(url, headers=headers)

                if response.status_code == 200:
                    return response

                last_response = response

                # 403이 아닌 다른 에러는 바로 raise
                if response.status_code != 403:
                    response.raise_for_status()

            except httpx.HTTPStatusError:
                raise
            except Exception:
                # 네트워크 에러 등은 다음 전략으로 계속
                continue

        # 모든 전략 실패 시 마지막 응답으로 raise
        if last_response is not None:
            last_response.raise_for_status()

        raise httpx.HTTPStatusError(
            "모든 fallback 전략이 실패했습니다.",
            request=None,
            response=last_response,
        )

    async def get_problem(self, problem_id: str) -> ProblemData:
        target_url = f"{self.BASE_URL}/{problem_id}"

        response = await self._fetch_with_fallback(problem_id)

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title_elem = soup.select_one("#problem_title")
        if not title_elem:
            raise ValueError("백준 문제 페이지를 파싱할 수 없습니다.")
        title = title_elem.get_text(strip=True)

        # Problem Info Table
        info_table = soup.select_one("#problem-info")
        time_limit = "N/A"
        memory_limit = "N/A"

        if info_table:
            tds = info_table.select("td")
            if len(tds) >= 2:
                time_limit = tds[0].get_text(strip=True)
                memory_limit = tds[1].get_text(strip=True)

        # Description & IO
        desc_elem = soup.select_one("#problem_description")
        input_elem = soup.select_one("#problem_input")
        output_elem = soup.select_one("#problem_output")

        description = desc_elem.get_text(strip=True) if desc_elem else ""
        input_desc = input_elem.get_text(strip=True) if input_elem else ""
        output_desc = output_elem.get_text(strip=True) if output_elem else ""

        # Test Cases
        test_cases = []
        idx = 1
        while True:
            input_node = soup.select_one(f"#sample-input-{idx}")
            output_node = soup.select_one(f"#sample-output-{idx}")

            if not input_node or not output_node:
                break

            test_cases.append(
                TestCase(input=input_node.get_text(), output=output_node.get_text())
            )
            idx += 1

        # Tags
        tags = []
        tags_div = soup.select_one("#problem_tags")
        if tags_div:
            for tag_link in tags_div.select("li a"):
                tags.append(tag_link.get_text(strip=True))

        return ProblemData(
            platform="BOJ",
            problem_id=problem_id,
            url=target_url,
            title=title,
            description=description,
            input_desc=input_desc,
            output_desc=output_desc,
            time_limit=time_limit,
            memory_limit=memory_limit,
            difficulty=None,
            tags=tags,
            test_cases=test_cases,
        )
