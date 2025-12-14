"""SERP (Search Engine Results Page) scraper."""

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ..config import ScraperConfig
from ..models import AdResult, MapsResult, OrganicResult, SerpResults
from .browser import BrowserManager
from .queries import build_google_url

logger = logging.getLogger(__name__)


class SerpScraper:
    """Scrapes Google Search results for local business discovery."""

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.browser_manager = BrowserManager(self.config)

    async def __aenter__(self):
        await self.browser_manager.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.browser_manager.close()

    async def search(
        self,
        business_type: str,
        location: str,
        max_results: int = 20,
    ) -> SerpResults:
        """
        Perform a Google search and extract all result types.

        Args:
            business_type: Type of business to search for
            location: Location to search in
            max_results: Maximum number of organic results to collect

        Returns:
            SerpResults containing ads, maps, and organic results
        """
        query = f"{business_type} {location}"
        url = build_google_url(query)

        results = SerpResults(query=query, location=location)

        async with self.browser_manager.new_context() as context:
            async with self.browser_manager.new_page(context) as page:
                try:
                    # Navigate to Google
                    logger.info("Searching: %s", query)
                    await page.goto(url, wait_until="domcontentloaded")

                    # Wait for results to load
                    await self._wait_for_results(page)

                    # Check for CAPTCHA/bot detection
                    if await self._check_captcha(page):
                        logger.warning(
                            "Google CAPTCHA detected. Try: --no-headless to solve manually, "
                            "use a VPN/proxy, or wait and retry later."
                        )
                        if self.config.debug:
                            await self._save_debug(page, "captcha_blocked")
                        return results

                    # Handle consent dialog if it appears
                    await self._handle_consent(page)

                    # Save debug screenshot if enabled
                    if self.config.debug:
                        await self._save_debug(page, "serp_results")

                    # Parse all result types
                    results.ads = await self._parse_ads(page)
                    results.maps = await self._parse_maps(page)
                    results.organic = await self._parse_organic(page, max_results)

                    logger.info(
                        "Found: %d ads, %d maps, %d organic",
                        len(results.ads),
                        len(results.maps),
                        len(results.organic),
                    )

                except PlaywrightTimeout as e:
                    logger.error("Timeout during search: %s", e)
                except Exception as e:
                    logger.error("Error during search: %s", e)
                    if self.config.debug:
                        await self._save_debug(page, "error_state")

        return results

    async def _wait_for_results(self, page: Page) -> None:
        """Wait for search results to load."""
        selectors = [
            "#search",
            "#rso",
            "[data-async-context]",
        ]

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                return
            except PlaywrightTimeout:
                continue

        # If no selector found, wait a bit anyway
        await asyncio.sleep(2)

    async def _handle_consent(self, page: Page) -> None:
        """Handle Google consent dialog if present."""
        consent_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            '[aria-label="Accept all"]',
            "#L2AGLb",
        ]

        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=1000):
                    await button.click()
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue

    async def _check_captcha(self, page: Page) -> bool:
        """Check if Google is showing a CAPTCHA or bot detection page."""
        try:
            content = await page.content()
            captcha_indicators = [
                "unusual traffic",
                "not a robot",
                "recaptcha",
                "captcha",
                "verify you're human",
                "automated queries",
            ]
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in captcha_indicators)
        except Exception:
            return False

    async def _parse_ads(self, page: Page) -> list[AdResult]:
        """Parse Google Ads from the SERP."""
        ads = []

        # Selectors for ad containers (Google changes these frequently)
        ad_selectors = [
            '[data-text-ad="1"]',
            '.uEierd',
            '[data-hveid] .commercial-unit-desktop-top',
            '#tads .uEierd',
            '#tads > div',
        ]

        for selector in ad_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for i, el in enumerate(elements):
                        try:
                            ad = await self._parse_single_ad(el, i + 1, is_top=True)
                            if ad:
                                ads.append(ad)
                        except Exception as e:
                            logger.debug("Failed to parse ad %d: %s", i, e)
                    break
            except Exception:
                continue

        # Also check for bottom ads
        bottom_selectors = ['#tadsb > div', '#bottomads .uEierd']
        for selector in bottom_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for i, el in enumerate(elements):
                    try:
                        ad = await self._parse_single_ad(
                            el, len(ads) + i + 1, is_top=False
                        )
                        if ad:
                            ads.append(ad)
                    except Exception:
                        continue
            except Exception:
                continue

        return ads

    async def _parse_single_ad(self, element, position: int, is_top: bool) -> Optional[AdResult]:
        """Parse a single ad element."""
        try:
            # Get headline
            headline_selectors = ['[role="heading"]', '.cfxYMc', 'h3', '.CCgQ5']
            headline = ""
            for sel in headline_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        headline = await el.inner_text()
                        if headline:
                            break
                except Exception:
                    continue

            if not headline:
                return None

            # Get destination URL
            link_el = await element.query_selector('a[href^="http"]')
            destination_url = ""
            if link_el:
                destination_url = await link_el.get_attribute("href") or ""

            # Get display URL
            display_url_selectors = ['.x2VHCd', '.qzEoUe', '.Zu0yb']
            display_url = ""
            for sel in display_url_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        display_url = await el.inner_text()
                        if display_url:
                            break
                except Exception:
                    continue

            # Get description
            desc_selectors = ['.MUxGbd', '.yXK7lf', '.lyLwlc']
            description = ""
            for sel in desc_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        description = await el.inner_text()
                        if description:
                            break
                except Exception:
                    continue

            return AdResult(
                position=position,
                headline=headline.strip(),
                display_url=display_url.strip(),
                destination_url=destination_url,
                description=description.strip(),
                is_top=is_top,
            )

        except Exception as e:
            logger.debug("Error parsing ad: %s", e)
            return None

    async def _parse_maps(self, page: Page) -> list[MapsResult]:
        """Parse Google Maps/Local Pack results from the SERP."""
        maps_results = []

        # Selectors for map pack (Google changes these frequently)
        container_selectors = [
            '[data-local-attribute="d3bn"]',
            '.VkpGBb',
            '[jscontroller="e3Wld"]',
            '.cXedhc',
            '[data-hveid] .rllt__details',
        ]

        elements = []
        for selector in container_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    logger.debug("Found %d maps results with selector: %s", len(elements), selector)
                    break
            except Exception:
                continue

        # Parse each map result
        for i, el in enumerate(elements[:3]):  # Usually only 3 in local pack
            try:
                result = await self._parse_single_maps_result(el, i + 1)
                if result:
                    maps_results.append(result)
            except Exception as e:
                logger.debug("Failed to parse maps result %d: %s", i, e)

        return maps_results

    async def _parse_single_maps_result(self, element, position: int) -> Optional[MapsResult]:
        """Parse a single maps/local pack result."""
        try:
            # Get business name
            name_selectors = [
                '.fontHeadlineSmall',
                '[role="heading"]',
                '.dbg0pd',
                '.OSrXXb',
                'span[class*="fontHeadline"]',
            ]
            name = ""
            for sel in name_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        name = await el.inner_text()
                        if name:
                            break
                except Exception:
                    continue

            if not name:
                # Try getting text from first link
                link = await element.query_selector('a')
                if link:
                    name = await link.inner_text()

            if not name:
                return None

            # Get rating
            rating = None
            rating_selectors = ['.yi40Hd', '.BTtC6e', '[aria-label*="rating"]']
            for sel in rating_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        text = await el.inner_text()
                        match = re.search(r'(\d+\.?\d*)', text)
                        if match:
                            rating = float(match.group(1))
                            break
                except Exception:
                    continue

            # Get review count
            review_count = None
            review_selectors = ['.RDApEe', '.UY7F9', '[aria-label*="review"]']
            for sel in review_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        text = await el.inner_text()
                        match = re.search(r'\(?([\d,]+)\)?', text)
                        if match:
                            review_count = int(match.group(1).replace(',', ''))
                            break
                except Exception:
                    continue

            # Get category
            category = None
            category_selectors = ['.rllt__details > div:nth-child(1)', '.W4Efsd']
            for sel in category_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        text = await el.inner_text()
                        # Category is usually the first line, often contains "·"
                        parts = text.split('·')
                        if parts:
                            category = parts[0].strip()
                            break
                except Exception:
                    continue

            # Get address
            address = ""
            address_selectors = ['.rllt__details', '.W4Efsd > span:last-child']
            for sel in address_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        text = await el.inner_text()
                        # Address is usually after the category
                        parts = text.split('·')
                        if len(parts) > 1:
                            address = parts[-1].strip()
                            break
                except Exception:
                    continue

            # Get phone (sometimes present)
            phone = None
            try:
                full_text = await element.inner_text()
                phone_match = re.search(r'(?:\+61|0)[2-478](?:[ -]?\d){8}', full_text)
                if phone_match:
                    phone = phone_match.group(0)
            except Exception:
                pass

            # Get website (from link)
            website = None
            try:
                links = await element.query_selector_all('a[href^="http"]')
                for link in links:
                    href = await link.get_attribute("href")
                    if href and "google.com" not in href:
                        website = href
                        break
            except Exception:
                pass

            return MapsResult(
                position=position,
                name=name.strip(),
                rating=rating,
                review_count=review_count,
                category=category,
                address=address,
                phone=phone,
                website=website,
            )

        except Exception as e:
            logger.debug("Error parsing maps result: %s", e)
            return None

    async def _parse_organic(self, page: Page, max_results: int) -> list[OrganicResult]:
        """Parse organic search results from the SERP."""
        organic_results = []

        # Selectors for organic results
        result_selectors = [
            '#rso > div > div',
            '#rso .g',
            '[data-hveid]:not([data-text-ad]) .g',
            '.MjjYud',
        ]

        elements = []
        for selector in result_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    logger.debug(
                        "Found %d organic results with selector: %s",
                        len(elements),
                        selector,
                    )
                    break
            except Exception:
                continue

        position = 0
        for el in elements:
            if position >= max_results:
                break

            try:
                result = await self._parse_single_organic(el, position + 1)
                if result:
                    organic_results.append(result)
                    position += 1
            except Exception as e:
                logger.debug("Failed to parse organic result: %s", e)

        return organic_results

    async def _parse_single_organic(self, element, position: int) -> Optional[OrganicResult]:
        """Parse a single organic search result."""
        try:
            # Get URL first (most reliable)
            link_el = await element.query_selector('a[href^="http"]')
            if not link_el:
                return None

            url = await link_el.get_attribute("href")
            if not url or "google.com" in url:
                return None

            # Extract domain
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
            except Exception:
                domain = url

            # Get title
            title_selectors = ['h3', '[role="heading"]', '.LC20lb']
            title = ""
            for sel in title_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        title = await el.inner_text()
                        if title:
                            break
                except Exception:
                    continue

            if not title:
                return None

            # Get snippet
            snippet_selectors = ['.VwiC3b', '.IsZvec', '.aCOpRe', '.st']
            snippet = ""
            for sel in snippet_selectors:
                try:
                    el = await element.query_selector(sel)
                    if el:
                        snippet = await el.inner_text()
                        if snippet:
                            break
                except Exception:
                    continue

            return OrganicResult(
                position=position,
                title=title.strip(),
                url=url,
                domain=domain,
                snippet=snippet.strip(),
            )

        except Exception as e:
            logger.debug("Error parsing organic result: %s", e)
            return None

    async def _save_debug(self, page: Page, name: str) -> None:
        """Save debug information (screenshot and HTML)."""
        import os

        os.makedirs(self.config.debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save screenshot
        screenshot_path = f"{self.config.debug_dir}/{name}_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        logger.debug("Saved screenshot: %s", screenshot_path)

        # Save HTML
        html_path = f"{self.config.debug_dir}/{name}_{timestamp}.html"
        html = await page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.debug("Saved HTML: %s", html_path)

    def _delay(self) -> None:
        """Add random delay between requests."""
        delay = random.uniform(
            self.config.search_delay_min,
            self.config.search_delay_max,
        )
        asyncio.sleep(delay)
