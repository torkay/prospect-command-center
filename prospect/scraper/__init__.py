"""SERP scraping module."""

# SerpAPI client (recommended - reliable, no CAPTCHA issues)
from .serpapi import SerpAPIClient, SerpAPIError, AuthenticationError, RateLimitError

# Playwright-based scraper (backup - may hit CAPTCHAs)
from .browser import BrowserManager
from .serp import SerpScraper
from .queries import build_search_query

__all__ = [
    # Primary (SerpAPI)
    "SerpAPIClient",
    "SerpAPIError",
    "AuthenticationError",
    "RateLimitError",
    # Legacy (Playwright)
    "BrowserManager",
    "SerpScraper",
    "build_search_query",
]
