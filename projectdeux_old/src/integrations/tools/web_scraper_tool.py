import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

# Try to import Selenium components for JS-rendered pages.
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class WebScraperTool:
    """
    A robust web scraper tool that first attempts to fetch and parse content using requests,
    then falls back to Selenium if necessary.
    """
    def __init__(self, 
                 user_agent: str = None, 
                 retries: int = 3, 
                 backoff_factor: float = 0.3, 
                 status_forcelist: tuple = (500, 502, 504), 
                 timeout: int = 10,
                 use_selenium_fallback: bool = True,
                 selenium_wait: int = 3):
        self.headers = {
            "User-Agent": user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.212 Safari/537.36"
            )
        }
        self.timeout = timeout
        self.use_selenium_fallback = use_selenium_fallback and SELENIUM_AVAILABLE
        self.selenium_wait = selenium_wait

        # Setup a requests session with retry logic.
        self.session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def execute(self, url: str, target: str = "p") -> str:
        """
        Scrape the given URL for elements matching the target.
        If the primary requests-based method returns empty content and Selenium is enabled,
        fall back to using Selenium.
        """
        content = self._requests_scrape(url, target)
        if not content.strip() and self.use_selenium_fallback:
            content = self._selenium_scrape(url, target)
        print(f"Scraped content from {url}: {content[:100]}...")  # Debug output
        return content

    def _requests_scrape(self, url: str, target: str = "p") -> str:
        """
        Scrape content from the URL using requests and BeautifulSoup.
        """
        try:
            response = self.session.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            # Use CSS selector if target contains '.' or '#', otherwise search by tag.
            if "." in target or "#" in target:
                elements = soup.select(target)
            else:
                elements = soup.find_all(target)
            # Join non-empty text from each element.
            text = "\n".join([el.get_text(strip=True) for el in elements if el.get_text(strip=True)])
            return text or f"No content found using target: {target}"
        except Exception as e:
            return f"Error scraping {url} with requests: {str(e)}"

    def _selenium_scrape(self, url: str, target: str = "p") -> str:
        """
        Scrape content using Selenium (headless Chrome) to handle JavaScript-rendered pages.
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            # Wait for content to load.
            time.sleep(self.selenium_wait)
            page_source = driver.page_source
            driver.quit()
            soup = BeautifulSoup(page_source, "lxml")
            if "." in target or "#" in target:
                elements = soup.select(target)
            else:
                elements = soup.find_all(target)
            text = "\n".join([el.get_text(strip=True) for el in elements if el.get_text(strip=True)])
            return text or f"No content found using target: {target}"
        except Exception as e:
            return f"Error scraping {url} with Selenium: {str(e)}"
