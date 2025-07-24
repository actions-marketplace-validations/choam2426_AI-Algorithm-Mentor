"""
Web crawler service for online judge platforms.

This module provides a clean, efficient interface for crawling problem information
from major online judge platforms with proper error handling and rate limiting.
"""

import re
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from .config import AppConfig
from .exceptions import CrawlerError
from .logger import get_logger, LogContext

logger = get_logger(__name__)


@dataclass(frozen=True)
class ProblemInfo:
    """Structured problem information from online judge platforms."""
    
    site: str
    problem_id: str
    title: str
    url: str
    difficulty: Optional[str] = None
    description: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    examples: List[Dict[str, str]] = field(default_factory=list)
    time_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    
    def to_formatted_string(self, max_description_length: int = 1000) -> str:
        """Convert problem info to LLM-friendly formatted string."""
        if not self.success:
            return f"""
❌ PROBLEM EXTRACTION FAILED
Site: {self.site}
URL: {self.url}
Error: {self.error_message}
"""
        
        lines = [
            "📚 PROBLEM INFORMATION",
            "=" * 50,
            "",
            f"🌐 Site: {self.site}",
            f"🔢 Problem ID: {self.problem_id}",
            f"📝 Title: {self.title}",
        ]
        
        if self.difficulty:
            lines.append(f"⚡ Difficulty: {self.difficulty}")
        
        lines.extend(["", f"🔗 URL: {self.url}", ""])
        
        # Constraints
        if self.time_limit or self.memory_limit:
            lines.extend(["⏱️ CONSTRAINTS", "-" * 12])
            if self.time_limit:
                lines.append(f"• Time Limit: {self.time_limit}")
            if self.memory_limit:
                lines.append(f"• Memory Limit: {self.memory_limit}")
            lines.append("")
        
        # Description
        if self.description:
            lines.extend(["📖 PROBLEM DESCRIPTION", "-" * 20])
            description = self.description
            if len(description) > max_description_length:
                description = description[:max_description_length] + "... [truncated]"
            lines.extend([description, ""])
        
        # Input/Output format
        if self.input_format:
            lines.extend(["📥 INPUT FORMAT", "-" * 14, self.input_format, ""])
        
        if self.output_format:
            lines.extend(["📤 OUTPUT FORMAT", "-" * 15, self.output_format, ""])
        
        # Examples
        if self.examples:
            lines.extend(["💡 EXAMPLES", "-" * 10])
            for i, example in enumerate(self.examples, 1):
                lines.extend([
                    f"Example {i}:",
                    "  Input:",
                    f"    {example.get('input', '').strip()}",
                    "  Output:",
                    f"    {example.get('output', '').strip()}",
                    ""
                ])
        
        return "\n".join(lines)


class BaseCrawler(ABC):
    """Abstract base class for platform-specific crawlers."""
    
    def __init__(self, driver: webdriver.Chrome, wait: WebDriverWait):
        self.driver = driver
        self.wait = wait
    
    @abstractmethod
    def crawl(self, url: str) -> ProblemInfo:
        """Crawl problem information from the given URL."""
        pass
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """Check if this crawler supports the given URL."""
        pass


class BaekjoonCrawler(BaseCrawler):
    """Crawler for Baekjoon Online Judge (acmicpc.net)."""
    
    def supports_url(self, url: str) -> bool:
        return "acmicpc.net" in url
    
    def crawl(self, url: str) -> ProblemInfo:
        """Crawl Baekjoon problem information."""
        try:
            self.driver.get(url)
            
            # Extract problem ID
            problem_id_match = re.search(r"/problem/(\d+)", url)
            problem_id = problem_id_match.group(1) if problem_id_match else "unknown"
            
            # Get title
            title = self.wait.until(
                EC.presence_of_element_located((By.ID, "problem_title"))
            ).text.strip()
            
            # Get description
            description = None
            try:
                desc_elem = self.driver.find_element(By.ID, "problem_description")
                description = desc_elem.text.strip()
            except Exception:
                pass
            
            # Get input/output format
            input_format = self._get_element_text(By.ID, "problem_input")
            output_format = self._get_element_text(By.ID, "problem_output")
            
            # Get examples
            examples = self._extract_examples()
            
            # Get constraints
            time_limit, memory_limit = self._extract_constraints()
            
            return ProblemInfo(
                site="Baekjoon",
                problem_id=problem_id,
                title=title,
                url=url,
                description=description,
                input_format=input_format,
                output_format=output_format,
                examples=examples,
                time_limit=time_limit,
                memory_limit=memory_limit
            )
            
        except Exception as e:
            return ProblemInfo(
                site="Baekjoon",
                problem_id="error",
                title="Crawling failed",
                url=url,
                success=False,
                error_message=str(e)
            )
    
    def _get_element_text(self, by: By, value: str) -> Optional[str]:
        """Safely get element text."""
        try:
            element = self.driver.find_element(by, value)
            return element.text.strip()
        except Exception:
            return None
    
    def _extract_examples(self) -> List[Dict[str, str]]:
        """Extract example input/output pairs."""
        examples = []
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "pre[id^='sample-input-']")
            outputs = self.driver.find_elements(By.CSS_SELECTOR, "pre[id^='sample-output-']")
            
            for inp, out in zip(inputs, outputs):
                examples.append({
                    "input": inp.text.strip(),
                    "output": out.text.strip()
                })
        except Exception:
            pass
        
        return examples
    
    def _extract_constraints(self) -> tuple[Optional[str], Optional[str]]:
        """Extract time and memory limits."""
        time_limit = memory_limit = None
        try:
            info_table = self.driver.find_element(By.ID, "problem-info")
            rows = info_table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    cell_text = cells[0].text.strip()
                    if "시간" in cell_text:
                        time_limit = cells[1].text.strip()
                    elif "메모리" in cell_text:
                        memory_limit = cells[1].text.strip()
        except Exception:
            pass
        
        return time_limit, memory_limit


class ProgrammersCrawler(BaseCrawler):
    """Crawler for Programmers (programmers.co.kr)."""
    
    def supports_url(self, url: str) -> bool:
        return "programmers.co.kr" in url
    
    def crawl(self, url: str) -> ProblemInfo:
        """Crawl Programmers problem information."""
        try:
            self.driver.get(url)
            time.sleep(5)  # JavaScript loading wait
            
            # Extract problem ID
            problem_match = re.search(r"/lessons/(\d+)", url)
            problem_id = problem_match.group(1) if problem_match else "unknown"
            
            # Get title
            title = "제목 추출 실패"
            title_selectors = [
                "h3.lesson-title",
                ".algorithm-title",
                "[data-cy='algorithm-title']",
                ".title",
                "h1", "h2", "h3",
                ".challenge-title",
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    potential_title = title_elem.text.strip()
                    if (potential_title and 
                        not potential_title.startswith("프로그래머스") and 
                        len(potential_title) > 3):
                        title = potential_title
                        break
                except Exception:
                    continue
            
            # Get difficulty
            difficulty = None
            difficulty_selectors = [
                ".algorithm-level", ".level", "[class*='level']", 
                ".difficulty", "[data-testid='level']"
            ]
            
            for selector in difficulty_selectors:
                try:
                    diff_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    difficulty = diff_elem.text.strip()
                    if difficulty and "Level" in difficulty:
                        break
                except Exception:
                    continue
            
            # Get description (partial)
            description = None
            desc_selectors = [
                ".guide-section-description", ".algorithm-description",
                ".lesson-content", "[data-cy='algorithm-description']",
                ".content", ".markdown"
            ]
            
            for selector in desc_selectors:
                try:
                    desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    desc_text = desc_elem.text.strip()
                    if desc_text and len(desc_text) > 10:
                        description = desc_text[:800]  # First 800 chars
                        break
                except Exception:
                    continue
            
            return ProblemInfo(
                site="Programmers",
                problem_id=problem_id,
                title=title,
                url=url,
                difficulty=difficulty,
                description=description
            )
            
        except Exception as e:
            return ProblemInfo(
                site="Programmers",
                problem_id="error",
                title="Crawling failed",
                url=url,
                success=False,
                error_message=str(e)
            )


class LeetCodeCrawler(BaseCrawler):
    """Crawler for LeetCode (leetcode.com)."""
    
    def supports_url(self, url: str) -> bool:
        return "leetcode.com" in url
    
    def crawl(self, url: str) -> ProblemInfo:
        """Crawl LeetCode problem information."""
        try:
            self.driver.get(url)
            time.sleep(8)  # GraphQL and React loading wait
            
            # Extract problem ID
            problem_match = re.search(r"/problems/([^/]+)", url)
            problem_id = problem_match.group(1) if problem_match else "unknown"
            
            # Get title
            title = "제목 추출 실패"
            title_selectors = [
                "[data-cy='question-title']",
                ".text-title-large",
                ".mr-2",
                "h1",
                ".css-v3d350",
                ".question-title",
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    potential_title = title_elem.text.strip()
                    if (potential_title and 
                        not potential_title.startswith("Sign") and 
                        len(potential_title) > 3):
                        # Remove problem number if included
                        clean_title = re.sub(r"^\d+\.\s*", "", potential_title)
                        title = clean_title if clean_title else potential_title
                        break
                except Exception:
                    continue
            
            # Get difficulty
            difficulty = None
            diff_selectors = [
                ".text-olive",   # Easy
                ".text-yellow",  # Medium
                ".text-pink",    # Hard
                "[diff='1']", "[diff='2']", "[diff='3']",
                ".difficulty",
            ]
            
            for selector in diff_selectors:
                try:
                    diff_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if "olive" in selector:
                        difficulty = "Easy"
                    elif "yellow" in selector:
                        difficulty = "Medium"
                    elif "pink" in selector:
                        difficulty = "Hard"
                    else:
                        difficulty = diff_elem.text.strip()
                    
                    if difficulty:
                        break
                except Exception:
                    continue
            
            # Get description (limited)
            description = None
            desc_selectors = [
                ".question-content",
                ".content__u3I1",
                "[data-track-load='description_content']",
                ".elfjS",
            ]
            
            for selector in desc_selectors:
                try:
                    desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    desc_text = desc_elem.text.strip()
                    if desc_text and len(desc_text) > 20:
                        description = desc_text[:1000]  # First 1000 chars
                        break
                except Exception:
                    continue
            
            if not description:
                description = "로그인이 필요하거나 JavaScript 렌더링 지연으로 인해 상세 정보 추출 제한"
            
            return ProblemInfo(
                site="LeetCode",
                problem_id=problem_id,
                title=title,
                url=url,
                difficulty=difficulty,
                description=description
            )
            
        except Exception as e:
            return ProblemInfo(
                site="LeetCode",
                problem_id="error",
                title="Crawling failed",
                url=url,
                success=False,
                error_message=str(e)
            )


class CodeforcesCrawler(BaseCrawler):
    """Crawler for Codeforces (codeforces.com)."""
    
    def supports_url(self, url: str) -> bool:
        return "codeforces.com" in url
    
    def crawl(self, url: str) -> ProblemInfo:
        """Crawl Codeforces problem information."""
        try:
            self.driver.get(url)
            
            # Extract problem ID
            problem_match = re.search(r"/problem/([^/]+/[^/]+)", url)
            if not problem_match:
                problem_match = re.search(r"/contest/(\d+)/problem/([A-Z]+)", url)
                problem_id = (
                    f"{problem_match.group(1)}{problem_match.group(2)}"
                    if problem_match else "unknown"
                )
            else:
                problem_id = problem_match.group(1)
            
            # Get title
            title = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".problem-statement .title")
                )
            ).text.strip()
            
            # Get time/memory limits
            time_limit = memory_limit = None
            try:
                time_elem = self.driver.find_element(By.CSS_SELECTOR, ".time-limit")
                time_limit = time_elem.text.strip()
            except Exception:
                pass
            
            try:
                memory_elem = self.driver.find_element(By.CSS_SELECTOR, ".memory-limit")
                memory_limit = memory_elem.text.strip()
            except Exception:
                pass
            
            # Get description
            description = None
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, ".problem-statement")
                paragraphs = desc_elem.find_elements(By.TAG_NAME, "p")
                if paragraphs:
                    description = paragraphs[0].text.strip()[:800]  # First paragraph, 800 chars
            except Exception:
                pass
            
            # Get examples
            examples = []
            try:
                input_elems = self.driver.find_elements(By.CSS_SELECTOR, ".input pre")
                output_elems = self.driver.find_elements(By.CSS_SELECTOR, ".output pre")
                
                for inp, out in zip(input_elems, output_elems):
                    examples.append({
                        "input": inp.text.strip(),
                        "output": out.text.strip()
                    })
            except Exception:
                pass
            
            return ProblemInfo(
                site="Codeforces",
                problem_id=problem_id,
                title=title,
                url=url,
                description=description,
                examples=examples,
                time_limit=time_limit,
                memory_limit=memory_limit
            )
            
        except Exception as e:
            return ProblemInfo(
                site="Codeforces",
                problem_id="error",
                title="Crawling failed",
                url=url,
                success=False,
                error_message=str(e)
            )


class HackerRankCrawler(BaseCrawler):
    """Crawler for HackerRank (hackerrank.com)."""
    
    def supports_url(self, url: str) -> bool:
        return "hackerrank.com" in url
    
    def crawl(self, url: str) -> ProblemInfo:
        """Crawl HackerRank problem information."""
        try:
            self.driver.get(url)
            time.sleep(5)  # Page loading wait
            
            # Extract problem ID
            problem_match = re.search(r"/challenges/([^/]+)", url)
            problem_id = problem_match.group(1) if problem_match else "unknown"
            
            # Get title
            title = "제목 추출 실패"
            title_selectors = [
                ".challenge-name",
                ".challenge-title",
                "h1.ui-icon-label",
                ".page-header-text",
                "h1",
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    potential_title = title_elem.text.strip()
                    if potential_title and len(potential_title) > 3:
                        title = potential_title
                        break
                except Exception:
                    continue
            
            # Get difficulty
            difficulty = None
            diff_selectors = [
                ".difficulty",
                ".challenge-difficulty",
                "[class*='difficulty']",
            ]
            
            for selector in diff_selectors:
                try:
                    diff_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    difficulty = diff_elem.text.strip()
                    if difficulty:
                        break
                except Exception:
                    continue
            
            # Get description (limited)
            description = None
            desc_selectors = [
                ".challenge-text",
                ".problem-statement",
                ".challenge-body-html",
                ".content",
            ]
            
            for selector in desc_selectors:
                try:
                    desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    desc_text = desc_elem.text.strip()
                    if desc_text and len(desc_text) > 20:
                        description = desc_text[:800]  # First 800 chars
                        break
                except Exception:
                    continue
            
            return ProblemInfo(
                site="HackerRank",
                problem_id=problem_id,
                title=title,
                url=url,
                difficulty=difficulty,
                description=description
            )
            
        except Exception as e:
            return ProblemInfo(
                site="HackerRank",
                problem_id="error",
                title="Crawling failed",
                url=url,
                success=False,
                error_message=str(e)
            )


class CrawlerService:
    """Main crawler service for online judge platforms."""
    
    SUPPORTED_PLATFORMS = {
        "acmicpc.net": "Baekjoon",
        "www.acmicpc.net": "Baekjoon",
        "programmers.co.kr": "Programmers",
        "school.programmers.co.kr": "Programmers",
        "leetcode.com": "LeetCode",
        "www.leetcode.com": "LeetCode",
        "codeforces.com": "Codeforces",
        "www.codeforces.com": "Codeforces",
        "hackerrank.com": "HackerRank",
        "www.hackerrank.com": "HackerRank",
    }
    
    def __init__(self, config: AppConfig):
        self.config = config
        self._driver: Optional[webdriver.Chrome] = None
        self._wait: Optional[WebDriverWait] = None
        self._crawlers: List[BaseCrawler] = []
    
    def __enter__(self):
        self._setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_driver()
    
    def _setup_driver(self) -> None:
        """Setup Chrome WebDriver with optimized options."""
        logger.info("🚀 Setting up Chrome WebDriver")
        
        chrome_options = Options()
        
        if self.config.crawler.headless:
            chrome_options.add_argument("--headless=new")
        
        # Performance optimizations
        performance_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-extensions",
            "--disable-images",
            "--window-size=1920,1080",
            "--memory-pressure-off",
            "--max_old_space_size=4096",
        ]
        
        for arg in performance_args:
            chrome_options.add_argument(arg)
        
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            self._driver = webdriver.Chrome(options=chrome_options)
            self._driver.set_page_load_timeout(self.config.crawler.timeout)
            self._wait = WebDriverWait(self._driver, self.config.crawler.timeout)
            
            # Initialize crawlers
            self._crawlers = [
                BaekjoonCrawler(self._driver, self._wait),
                ProgrammersCrawler(self._driver, self._wait),
                LeetCodeCrawler(self._driver, self._wait),
                CodeforcesCrawler(self._driver, self._wait),
                HackerRankCrawler(self._driver, self._wait),
            ]
            
            logger.info("✅ Chrome WebDriver initialized successfully")
            
        except Exception as e:
            raise CrawlerError(f"Failed to setup Chrome WebDriver: {str(e)}")
    
    def _cleanup_driver(self) -> None:
        """Clean up WebDriver resources."""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("🔴 Chrome WebDriver closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebDriver: {e}")
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """Extract online judge URLs from text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        # Filter for supported platforms
        supported_urls = []
        for url in urls:
            try:
                domain = urlparse(url).netloc.lower()
                if any(platform in domain for platform in self.SUPPORTED_PLATFORMS):
                    supported_urls.append(url)
            except Exception:
                continue
        
        logger.info(f"🎯 Found {len(supported_urls)} supported URLs from {len(urls)} total URLs")
        return supported_urls
    
    def crawl_url(self, url: str) -> ProblemInfo:
        """Crawl problem information from a single URL."""
        if not self._driver or not self._wait:
            raise CrawlerError("Driver not initialized. Use context manager.")
        
        with LogContext(logger, {"url": url}):
            logger.info("🔍 Starting to crawl URL")
            
            # Find appropriate crawler
            crawler = None
            for c in self._crawlers:
                if c.supports_url(url):
                    crawler = c
                    break
            
            if not crawler:
                return ProblemInfo(
                    site="Unknown",
                    problem_id="unknown",
                    title="Unsupported platform",
                    url=url,
                    success=False,
                    error_message=f"Unsupported platform. Supported: {', '.join(self.SUPPORTED_PLATFORMS.values())}"
                )
            
            try:
                result = crawler.crawl(url)
                if result.success:
                    logger.info(f"✅ Successfully crawled: {result.title}")
                else:
                    logger.warning(f"⚠️ Crawling failed: {result.error_message}")
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return ProblemInfo(
                    site="Unknown",
                    problem_id="error",
                    title="Crawling error",
                    url=url,
                    success=False,
                    error_message=str(e)
                )
    
    def crawl_problems_from_text(self, text: str) -> List[ProblemInfo]:
        """Extract URLs from text and crawl all problems."""
        urls = self.extract_urls_from_text(text)
        
        if not urls:
            logger.info("📝 No supported URLs found in text")
            return []
        
        results = []
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Processing URL...")
            
            result = self.crawl_url(url)
            results.append(result)
            
            # Rate limiting
            if i < len(urls):
                time.sleep(self.config.crawler.delay_between_requests)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"🎉 Crawling completed: {success_count}/{len(results)} successful")
        
        return results


# Legacy support functions
def crawl_problems_from_text(text: str, headless: bool = True) -> List[ProblemInfo]:
    """Legacy function for backward compatibility."""
    logger.warning("🚨 Using deprecated crawl_problems_from_text function. Please migrate to CrawlerService.")
    
    from .config import AppConfig, GitHubConfig, LLMConfig, CrawlerConfig, LLMProvider
    import os
    
    try:
        temp_config = AppConfig(
            github=GitHubConfig(
                token=os.getenv("GITHUB_TOKEN", ""),
                repository=os.getenv("GITHUB_REPOSITORY", ""),
                commit_sha=os.getenv("GITHUB_SHA", "")
            ),
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4o",
                api_key="dummy"
            ),
            crawler=CrawlerConfig(headless=headless)
        )
        
        with CrawlerService(temp_config) as service:
            return service.crawl_problems_from_text(text)
            
    except Exception as e:
        logger.error(f"❌ Legacy function failed: {e}")
        return []


def format_problem_for_llm(problem: ProblemInfo, **kwargs) -> str:
    """Legacy function for backward compatibility."""
    logger.warning("🚨 Using deprecated format_problem_for_llm function. Use ProblemInfo.to_formatted_string() instead.")
    return problem.to_formatted_string(**kwargs)