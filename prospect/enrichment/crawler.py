"""Website crawler for fetching and analyzing business websites."""

import asyncio
import logging
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import ScraperConfig
from ..models import CrawlResult, WebsiteSignals, Prospect
from .contacts import extract_emails, extract_phones
from .technology import detect_cms, detect_tracking, detect_booking_system
from ..validation import filter_emails_for_domain
from ..dedup import normalize_domain
from .. import _native

logger = logging.getLogger(__name__)


class WebsiteCrawler:
    """Crawls websites to extract marketing signals."""

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        """Initialize the HTTP client."""
        if self._client:
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.enrichment_timeout / 1000),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-AU,en;q=0.9",
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str) -> CrawlResult:
        """
        Fetch a URL and return the result.

        Args:
            url: URL to fetch

        Returns:
            CrawlResult with success status and content
        """
        if not self._client:
            await self.start()

        # Ensure URL has scheme
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        result = CrawlResult(url=url, success=False)

        try:
            start_time = time.time()
            response = await self._client.get(url)
            load_time = int((time.time() - start_time) * 1000)

            result.status_code = response.status_code
            result.load_time_ms = load_time
            result.final_url = str(response.url)

            if response.status_code == 200:
                result.success = True
                result.html = response.text

        except httpx.TimeoutException:
            result.error = "Timeout"
            logger.debug("Timeout fetching %s", url)
        except httpx.ConnectError as e:
            result.error = f"Connection error: {e}"
            logger.debug("Connection error fetching %s: %s", url, e)
        except Exception as e:
            result.error = str(e)
            logger.debug("Error fetching %s: %s", url, e)

        return result

    async def enrich_prospect(self, prospect: Prospect) -> Prospect:
        """
        Enrich a prospect with website signals.

        Args:
            prospect: Prospect to enrich

        Returns:
            Prospect with signals populated
        """
        if not prospect.website:
            # No website - high opportunity
            prospect.signals = WebsiteSignals(url="", reachable=False)
            return prospect

        signals = await self.analyze_website(prospect.website)
        prospect.signals = signals

        # Filter emails to only include those matching the business domain
        # This prevents cross-contamination (e.g., billy@bkc.media on fallonsolutions.com.au)
        business_domain = prospect.domain or normalize_domain(prospect.website)
        if business_domain:
            valid_emails = filter_emails_for_domain(signals.emails, business_domain)
            logger.debug(
                "Filtered %d -> %d emails for domain %s",
                len(signals.emails),
                len(valid_emails),
                business_domain,
            )
        else:
            valid_emails = signals.emails

        # Merge validated contact info
        for email in valid_emails:
            if email not in prospect.emails:
                prospect.emails.append(email)

        if signals.phones and not prospect.phone:
            prospect.phone = signals.phones[0]

        return prospect

    async def analyze_website(self, url: str) -> WebsiteSignals:
        """
        Analyze a website and extract marketing signals.

        Args:
            url: Website URL to analyze

        Returns:
            WebsiteSignals with all detected signals
        """
        signals = WebsiteSignals(url=url)

        # Fetch the main page
        result = await self.fetch(url)

        if not result.success:
            return signals

        signals.reachable = True
        signals.load_time_ms = result.load_time_ms

        # Parse HTML
        try:
            soup = BeautifulSoup(result.html, "lxml")
        except Exception as e:
            logger.debug("Failed to parse HTML for %s: %s", url, e)
            return signals

        # Extract each signal type with error handling
        try:
            signals.emails = extract_emails(result.html)
        except Exception as e:
            logger.debug("Failed to extract emails from %s: %s", url, e)

        try:
            signals.phones = extract_phones(result.html)
        except Exception as e:
            logger.debug("Failed to extract phones from %s: %s", url, e)

        try:
            signals.cms = detect_cms(result.html)
        except Exception as e:
            logger.debug("Failed to detect CMS for %s: %s", url, e)

        try:
            tracking = detect_tracking(result.html)
            signals.has_google_analytics = tracking.get("google_analytics", False)
            signals.has_facebook_pixel = tracking.get("facebook_pixel", False)
            signals.has_google_ads = tracking.get("google_ads", False)
        except Exception as e:
            logger.debug("Failed to detect tracking for %s: %s", url, e)

        try:
            signals.has_booking_system = detect_booking_system(result.html)
        except Exception as e:
            logger.debug("Failed to detect booking system for %s: %s", url, e)

        # Extract metadata + social links (native Rust or BeautifulSoup fallback)
        try:
            if _native.extract_html_metadata is not None:
                meta = _native.extract_html_metadata(result.html)
                signals.title = meta.get("title")
                signals.meta_description = meta.get("meta_description")
                signals.social_links = meta.get("social_links", [])
            else:
                title_tag = soup.find("title")
                if title_tag:
                    signals.title = title_tag.get_text(strip=True)

                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    signals.meta_description = meta_desc.get("content", "")

                signals.social_links = self._extract_social_links(soup)
        except Exception:
            pass

        return signals

    def _extract_social_links(self, soup: BeautifulSoup) -> list[str]:
        """Extract social media profile links from page."""
        social_domains = [
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "linkedin.com",
            "youtube.com",
            "tiktok.com",
        ]

        social_links = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            for domain in social_domains:
                if domain in href and href not in social_links:
                    social_links.append(href)
                    break

        return social_links

    async def enrich_prospects(
        self,
        prospects: list[Prospect],
        max_concurrent: int = 5,
    ) -> list[Prospect]:
        """
        Enrich multiple prospects concurrently.

        Args:
            prospects: List of prospects to enrich
            max_concurrent: Maximum concurrent requests

        Returns:
            List of enriched prospects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_semaphore(prospect: Prospect) -> Prospect:
            async with semaphore:
                return await self.enrich_prospect(prospect)

        tasks = [enrich_with_semaphore(p) for p in prospects]
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful enrichments
        results = []
        for i, result in enumerate(enriched):
            if isinstance(result, Exception):
                logger.warning("Failed to enrich prospect %s: %s", prospects[i].name, result)
                results.append(prospects[i])  # Return original
            else:
                results.append(result)

        return results
