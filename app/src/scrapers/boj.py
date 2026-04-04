import asyncio
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src.logger import logger

from .base import BaseScraper
from .models import ProblemData, TestCase

# solved.ac 레벨 -> 사람이 읽을 수 있는 난이도 문자열 매핑
_SOLVED_AC_LEVEL_NAMES: dict[int, str] = {
    0: "Unrated",
    1: "Bronze V", 2: "Bronze IV", 3: "Bronze III", 4: "Bronze II", 5: "Bronze I",
    6: "Silver V", 7: "Silver IV", 8: "Silver III", 9: "Silver II", 10: "Silver I",
    11: "Gold V", 12: "Gold IV", 13: "Gold III", 14: "Gold II", 15: "Gold I",
    16: "Platinum V", 17: "Platinum IV", 18: "Platinum III", 19: "Platinum II", 20: "Platinum I",
    21: "Diamond V", 22: "Diamond IV", 23: "Diamond III", 24: "Diamond II", 25: "Diamond I",
    26: "Ruby V", 27: "Ruby IV", 28: "Ruby III", 29: "Ruby II", 30: "Ruby I",
}


class BOJScraper(BaseScraper):
    BASE_URL = "https://www.acmicpc.net/problem"
    SOLVED_AC_API = "https://solved.ac/api/v3/problem/show"

    async def _fetch_from_solved_ac(self, problem_id: str) -> Optional[dict]:
        """solved.ac API에서 문제 메타데이터를 가져옵니다.

        Returns:
            파싱된 JSON dict (title, tags, level 등) 또는 실패 시 None.
            이 메서드는 절대 예외를 발생시키지 않습니다.
        """
        url = f"{self.SOLVED_AC_API}?problemId={problem_id}"
        try:
            logger.info(f"[BOJ #{problem_id}] solved.ac API 조회 시도: {url}")
            response = await self.client.get(url, timeout=10.0)
            if response.status_code != 200:
                logger.warning(
                    f"[BOJ #{problem_id}] solved.ac API 응답 실패: "
                    f"status={response.status_code}"
                )
                return None

            data = response.json()
            logger.info(
                f"[BOJ #{problem_id}] solved.ac API 조회 성공: "
                f"level={data.get('level')}, title={data.get('titleKo', '')}"
            )
            return data
        except Exception as exc:
            logger.warning(
                f"[BOJ #{problem_id}] solved.ac API 호출 중 오류 발생: {exc}"
            )
            return None

    def _extract_solved_ac_tags(self, solved_data: dict) -> list[str]:
        """solved.ac 응답에서 태그 이름 목록을 추출합니다."""
        tags: list[str] = []
        for tag_obj in solved_data.get("tags", []):
            display_names = tag_obj.get("displayNames", [])
            # 한국어 우선, 없으면 영어
            ko_name = next(
                (d["name"] for d in display_names if d.get("language") == "ko"),
                None,
            )
            en_name = next(
                (d["name"] for d in display_names if d.get("language") == "en"),
                None,
            )
            name = ko_name or en_name or tag_obj.get("key", "")
            if name:
                tags.append(name)
        return tags

    def _solved_ac_level_to_str(self, level: int) -> str:
        """solved.ac 레벨 숫자를 난이도 문자열로 변환합니다."""
        return _SOLVED_AC_LEVEL_NAMES.get(level, f"Level {level}")

    async def _fetch_with_fallback(self, problem_id: str) -> httpx.Response:
        """
        최대 4번의 fallback 전략으로 BOJ 페이지를 가져옵니다.
        1) HTTP/1.1 + 기본 브라우저 헤더
        2) HTTP/2 + Client Hints 포함 헤더
        3) URL 변형: 끝 슬래시 추가
        4) URL 변형: view=standard
        모든 전략 실패 시 403 그대로 전달
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

        # 전략 3, 4: URL 변형 + 동일 헤더
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
                    logger.debug(
                        f"[BOJ #{problem_id}] {retry_delays[i]}초 대기 후 "
                        f"전략 {i + 1} 시도"
                    )
                    await asyncio.sleep(retry_delays[i])

                logger.info(
                    f"[BOJ #{problem_id}] 전략 {i + 1}/4 시도: {strategy_name} "
                    f"-> {url}"
                )

                if use_http2:
                    # HTTP/2 클라이언트 생성
                    async with httpx.AsyncClient(http2=True, timeout=30.0) as h2_client:
                        response = await h2_client.get(url, headers=headers)
                else:
                    response = await self.client.get(url, headers=headers)

                if response.status_code == 200:
                    logger.info(
                        f"[BOJ #{problem_id}] 전략 {i + 1} 성공: "
                        f"{strategy_name} (status=200)"
                    )
                    return response

                logger.warning(
                    f"[BOJ #{problem_id}] 전략 {i + 1} 실패: "
                    f"{strategy_name} (status={response.status_code})"
                )
                last_response = response

                # 403이 아닌 다른 에러는 바로 raise
                if response.status_code != 403:
                    response.raise_for_status()

            except httpx.HTTPStatusError:
                raise
            except Exception as exc:
                logger.warning(
                    f"[BOJ #{problem_id}] 전략 {i + 1} 네트워크 오류: "
                    f"{strategy_name} -> {exc}"
                )
                # 네트워크 에러 등은 다음 전략으로 계속
                continue

        # 모든 전략 실패
        logger.error(
            f"[BOJ #{problem_id}] 모든 4개 전략 실패. "
            f"BOJ Cloudflare 차단으로 직접 스크래핑이 실패했습니다. "
            f"README.md fallback을 시도합니다. "
            f"BaekjoonHub 확장 사용을 권장합니다."
        )

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

        # Tags (from BOJ page)
        tags: list[str] = []
        tags_div = soup.select_one("#problem_tags")
        if tags_div:
            for tag_link in tags_div.select("li a"):
                tags.append(tag_link.get_text(strip=True))

        # solved.ac 보조 데이터로 enrichment
        difficulty: Optional[str] = None
        solved_ac_level: Optional[int] = None

        solved_data = await self._fetch_from_solved_ac(problem_id)
        if solved_data:
            level = solved_data.get("level")
            if level is not None:
                solved_ac_level = level
                difficulty = self._solved_ac_level_to_str(level)

            # 태그가 BOJ 페이지에서 비어 있으면 solved.ac에서 가져옴
            if not tags:
                solved_tags = self._extract_solved_ac_tags(solved_data)
                if solved_tags:
                    logger.info(
                        f"[BOJ #{problem_id}] BOJ 태그 없음, "
                        f"solved.ac 태그 {len(solved_tags)}개 사용"
                    )
                    tags = solved_tags

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
            difficulty=difficulty,
            tags=tags,
            test_cases=test_cases,
            solved_ac_level=solved_ac_level,
        )
