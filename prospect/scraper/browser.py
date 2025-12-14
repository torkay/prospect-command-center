"""Browser management with Playwright and stealth measures."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

from ..config import ScraperConfig

# Initialize stealth configuration
stealth = Stealth(
    navigator_platform_override="MacIntel",
    navigator_languages_override=("en-AU", "en"),
)

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser instances with stealth configuration."""

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        """Start the browser."""
        if self._browser:
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
            ],
        )
        logger.debug("Browser started (headless=%s)", self.config.headless)

    async def close(self) -> None:
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.debug("Browser closed")

    @asynccontextmanager
    async def new_context(self):
        """Create a new browser context with stealth settings."""
        if not self._browser:
            await self.start()

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-AU",
            timezone_id="Australia/Sydney",
            geolocation={"latitude": -33.8688, "longitude": 151.2093},
            permissions=["geolocation"],
        )

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def new_page(self, context: Optional[BrowserContext] = None):
        """Create a new page with stealth measures applied."""
        if context:
            page = await context.new_page()
        else:
            if not self._browser:
                await self.start()
            context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-AU",
                timezone_id="Australia/Sydney",
            )
            page = await context.new_page()

        # Apply stealth measures
        await stealth.apply_stealth_async(page)

        # Set default timeout
        page.set_default_timeout(self.config.browser_timeout)

        try:
            yield page
        finally:
            await page.close()
            if not context:
                await page.context.close()

    async def test_connection(self) -> bool:
        """Test that the browser can connect to Google."""
        try:
            async with self.new_page() as page:
                await page.goto("https://www.google.com.au", wait_until="domcontentloaded")
                title = await page.title()
                return "google" in title.lower()
        except Exception as e:
            logger.error("Browser connection test failed: %s", e)
            return False
