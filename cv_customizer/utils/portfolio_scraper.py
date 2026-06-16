"""Portfolio Website Scraping Utilities"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Result from web scraping"""
    content: str
    url: str
    title: str
    sections: Dict[str, str]
    extraction_method: str
    confidence: float
    error: Optional[str] = None


class PortfolioScraper:
    """Scrape portfolio websites to extract CV data"""

    TIMEOUT = 10
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    @classmethod
    def scrape_url(cls, url: str, headless: bool = True) -> ScrapingResult:
        """
        Scrape portfolio website
        
        Args:
            url: Portfolio URL
            headless: Run browser in headless mode
            
        Returns:
            ScrapingResult with extracted content
        """
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        logger.info(f"Scraping portfolio: {url}")

        try:
            # Try Selenium first (for JavaScript-heavy sites)
            return cls._scrape_with_selenium(url, headless)
        except ImportError:
            logger.warning("Selenium not available, trying BeautifulSoup")
            try:
                return cls._scrape_with_beautifulsoup(url)
            except ImportError:
                raise RuntimeError("No scraping libraries available")

    @classmethod
    def _scrape_with_selenium(
        cls, url: str, headless: bool = True
    ) -> ScrapingResult:
        """Scrape using Selenium (handles JavaScript)"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options

            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument(f"user-agent={cls.USER_AGENT}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(options=chrome_options)
            try:
                driver.set_page_load_timeout(cls.TIMEOUT)
                driver.get(url)

                # Wait for page to load
                WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
                )

                # Extract page title
                title = driver.title

                # Get page content
                content = driver.page_source
                
                # Extract text
                text_element = driver.find_element(By.TAG_NAME, "body")
                text = text_element.text if text_element else ""

                logger.info(f"Scraped {len(text)} chars from {url}")

                sections = cls._extract_sections_from_text(text)

                return ScrapingResult(
                    content=content,
                    url=url,
                    title=title,
                    sections=sections,
                    extraction_method="selenium",
                    confidence=0.90,
                )
            finally:
                driver.quit()

        except ImportError:
            raise
        except Exception as e:
            logger.error(f"Selenium scraping failed: {e}")
            return ScrapingResult(
                content="",
                url=url,
                title="",
                sections={},
                extraction_method="selenium",
                confidence=0.0,
                error=str(e),
            )

    @classmethod
    def _scrape_with_beautifulsoup(cls, url: str) -> ScrapingResult:
        """Scrape using BeautifulSoup (static content only)"""
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": cls.USER_AGENT}
            
            response = requests.get(url, headers=headers, timeout=cls.TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.text if title_tag else ""

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            logger.info(f"Scraped {len(text)} chars from {url}")

            sections = cls._extract_sections_from_text(text)

            return ScrapingResult(
                content=response.text,
                url=url,
                title=title,
                sections=sections,
                extraction_method="beautifulsoup",
                confidence=0.75,
            )

        except ImportError:
            raise
        except Exception as e:
            logger.error(f"BeautifulSoup scraping failed: {e}")
            return ScrapingResult(
                content="",
                url=url,
                title="",
                sections={},
                extraction_method="beautifulsoup",
                confidence=0.0,
                error=str(e),
            )

    @classmethod
    def _extract_sections_from_text(cls, text: str) -> Dict[str, str]:
        """Extract sections from scraped text"""
        sections = {}
        
        section_keywords = {
            "about": ["ABOUT", "BIO", "BIOGRAPHY", "PROFILE"],
            "experience": ["EXPERIENCE", "WORK", "EMPLOYMENT", "CAREER"],
            "projects": ["PROJECTS", "PORTFOLIO", "WORK SAMPLES"],
            "skills": ["SKILLS", "EXPERTISE", "TECHNOLOGIES"],
            "education": ["EDUCATION", "QUALIFICATIONS", "DEGREE"],
            "contact": ["CONTACT", "REACH ME", "GET IN TOUCH"],
        }

        text_lines = text.split("\n")
        current_section = None
        current_content = []

        for line in text_lines:
            line_upper = line.upper().strip()
            
            # Check for section headers
            found_section = False
            for section_name, keywords in section_keywords.items():
                if any(keyword in line_upper for keyword in keywords):
                    if current_section:
                        sections[current_section] = "\n".join(current_content).strip()
                    
                    current_section = section_name
                    current_content = []
                    found_section = True
                    break
            
            if not found_section and current_section and line.strip():
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        """Extract email address from text"""
        import re
        
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        """Extract phone number from text"""
        import re
        
        phone_patterns = [
            r"\+?1?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})",
            r"\+\d{1,3}\s?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}",
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    @classmethod
    def extract_social_links(cls, content: str) -> Dict[str, str]:
        """Extract social media links"""
        import re
        
        links = {}
        
        patterns = {
            "linkedin": r"https?://(?:www\.)?linkedin\.com/in/[\w-]+",
            "github": r"https?://(?:www\.)?github\.com/[\w-]+",
            "twitter": r"https?://(?:www\.)?twitter\.com/[\w-]+",
            "portfolio": r"https?://[\w.-]+(?:\.[\w-]+)+",
        }

        for name, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                links[name] = match.group(0)

        return links
