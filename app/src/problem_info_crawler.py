from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
import httpx

from .logger import logger


class _BojProblemParser(HTMLParser):
    """Lightweight HTML parser to extract BOJ problem sections.

    Captures text inside elements with ids:
    - problem_title
    - problem_description
    - problem_input
    - problem_output
    - sample-input-{n}
    - sample-output-{n}
    """

    TARGET_IDS = {
        "problem_title",
        "problem_description",
        "problem_input",
        "problem_output",
    }

    SAMPLE_INPUT_RE = re.compile(r"^sample-input-(\d+)$")
    SAMPLE_OUTPUT_RE = re.compile(r"^sample-output-(\d+)$")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buffers: Dict[str, List[str]] = {tid: [] for tid in self.TARGET_IDS}
        self._sample_inputs: Dict[int, List[str]] = {}
        self._sample_outputs: Dict[int, List[str]] = {}
        self._active_key: Optional[Tuple[str, Optional[int]]] = None
        self._stack: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        self._stack.append(tag)

        # Preserve line breaks in preformatted blocks
        if tag.lower() == "br" and self._active_key is not None:
            key, idx = self._active_key
            self._append_to_key(key, "\n", idx)

        elem_id = attr.get("id")
        if not elem_id:
            return

        if elem_id in self.TARGET_IDS:
            self._active_key = (elem_id, None)
            return

        m_in = self.SAMPLE_INPUT_RE.match(elem_id)
        if m_in:
            idx = int(m_in.group(1))
            self._active_key = ("sample_input", idx)
            self._sample_inputs.setdefault(idx, [])
            return

        m_out = self.SAMPLE_OUTPUT_RE.match(elem_id)
        if m_out:
            idx = int(m_out.group(1))
            self._active_key = ("sample_output", idx)
            self._sample_outputs.setdefault(idx, [])
            return

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()
        # Deactivate on closing the target element
        if self._active_key is None:
            return
        # When a block element ends that likely started the target, reset
        if tag.lower() in {"div", "h1", "section", "pre"}:
            self._active_key = None

    def handle_data(self, data: str) -> None:
        if self._active_key is None:
            return
        text = unescape(data)
        if not text:
            return
        key, idx = self._active_key
        self._append_to_key(key, text, idx)

    def _append_to_key(self, key: str, text: str, idx: Optional[int]) -> None:
        if key in self.TARGET_IDS:
            self._buffers[key].append(text)
        elif key == "sample_input" and idx is not None:
            self._sample_inputs.setdefault(idx, []).append(text)
        elif key == "sample_output" and idx is not None:
            self._sample_outputs.setdefault(idx, []).append(text)

    def result(self) -> Dict[str, object]:
        def join(parts: List[str]) -> str:
            return "".join(parts).strip()

        title = join(self._buffers.get("problem_title", []))
        desc = join(self._buffers.get("problem_description", []))
        in_txt = join(self._buffers.get("problem_input", []))
        out_txt = join(self._buffers.get("problem_output", []))

        # Order samples by index
        samples: List[Tuple[int, str, str]] = []
        for i in sorted(set(self._sample_inputs.keys()) | set(self._sample_outputs.keys())):
            si = join(self._sample_inputs.get(i, []))
            so = join(self._sample_outputs.get(i, []))
            samples.append((i, si, so))

        return {
            "title": title,
            "description": desc,
            "input": in_txt,
            "output": out_txt,
            "samples": samples,
        }


def _fetch_html(url: str, timeout: float = 20.0) -> str:
    """Fetch HTML trying multiple profiles; 쿠키 없이 최대한 403 회피.

    순서:
    1) HTTP/1.1 + 기본 브라우저 헤더
    2) HTTP/2 + Client Hints 포함 헤더
    3) URL 변형: 끝 슬래시 추가, view=standard
    4) 그래도 실패 시 403 그대로 전달
    """
    base_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    )

    profiles = [
        ({
            "User-Agent": base_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.acmicpc.net/",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }, False),
        ({
            "User-Agent": base_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.acmicpc.net/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Site": "same-origin",
            "Sec-CH-UA": '\"Chromium\";v=\"127\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"127\"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '\"Windows\"',
            "Accept-Encoding": "gzip, deflate, br",
        }, True),
    ]

    url_candidates = [
        url,
        url if url.endswith("/") else url + "/",
        url + ("&" if "?" in url else "?") + "view=standard",
    ]

    last_status = None
    last_url = None
    for headers, http2 in profiles:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True, http2=http2) as client:
            for u in url_candidates:
                resp = client.get(u)
                if resp.status_code == 200:
                    return resp.text
                last_status = resp.status_code
                last_url = str(resp.request.url)
    raise httpx.HTTPStatusError(
        f"Client error '{last_status}' for url '{last_url}'", request=None, response=None
    )


def crawl_boj_problem_markdown(url: str) -> str:
    """주어진 BOJ 문제 URL에서 핵심 정보를 수집하여 마크다운 문자열로 반환합니다.

    수집 항목: 제목, 설명, 입력, 출력, 예제 입출력
    """
    logger.info(f"🔎 Fetch BOJ problem: {url}")
    html = _fetch_html(url)

    parser = _BojProblemParser()
    parser.feed(html)
    data = parser.result()

    title = str(data.get("title") or "")
    description = str(data.get("description") or "")
    input_desc = str(data.get("input") or "")
    output_desc = str(data.get("output") or "")
    samples: List[Tuple[int, str, str]] = data.get("samples")  # type: ignore[assignment]
    samples = samples or []

    md_lines: List[str] = []
    md_lines.append(f"# {title}" if title else "# 문제 정보")
    md_lines.append("")
    md_lines.append(f"- URL: {url}")
    md_lines.append("")

    if description:
        md_lines.append("## 문제 설명")
        md_lines.append(description)
        md_lines.append("")

    if input_desc:
        md_lines.append("## 입력")
        md_lines.append(input_desc)
        md_lines.append("")

    if output_desc:
        md_lines.append("## 출력")
        md_lines.append(output_desc)
        md_lines.append("")

    if samples:
        md_lines.append("## 예제")
        for idx, si, so in samples:
            if si:
                md_lines.append(f"### 예제 {idx} 입력")
                md_lines.append("```")
                md_lines.append(si)
                md_lines.append("```")
            if so:
                md_lines.append(f"### 예제 {idx} 출력")
                md_lines.append("```")
                md_lines.append(so)
                md_lines.append("```")
        md_lines.append("")

    result = "\n".join(md_lines).strip() + "\n"
    logger.info("✅ BOJ problem info crawled")
    return result

if __name__ == "__main__":
    print(crawl_boj_problem_markdown("https://www.acmicpc.net/problem/1000"))