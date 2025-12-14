"""
SerpAPI client for Google Search results.

Replaces Playwright-based scraping with reliable API access.
"""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..models import SerpResults, AdResult, MapsResult, OrganicResult
from ..config import DIRECTORY_DOMAINS

logger = logging.getLogger(__name__)

# Australian state abbreviations to full names
AU_STATES = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "WA": "Western Australia",
    "SA": "South Australia",
    "TAS": "Tasmania",
    "ACT": "Australian Capital Territory",
    "NT": "Northern Territory",
}


def normalize_au_location(location: str) -> str:
    """
    Normalize Australian location strings for SerpAPI.

    SerpAPI prefers formats like:
    - "Sydney, New South Wales, Australia"
    - "Brisbane, Queensland, Australia"

    This function converts:
    - "Brisbane, QLD" -> "Brisbane, Queensland, Australia"
    - "Sydney NSW" -> "Sydney, New South Wales, Australia"
    - "Melbourne" -> "Melbourne, Australia"

    Args:
        location: User-provided location string

    Returns:
        SerpAPI-compatible location string
    """
    # Clean up the input
    location = location.strip()

    # Check if already has "Australia" - if so, might already be formatted
    if "australia" in location.lower():
        return location

    # Try to extract city and state
    # Common formats: "City, STATE", "City STATE", "City, State"
    parts = [p.strip() for p in location.replace(",", " ").split()]

    if len(parts) >= 2:
        # Check if last part is a state abbreviation
        last_part = parts[-1].upper()
        if last_part in AU_STATES:
            city = " ".join(parts[:-1])
            state = AU_STATES[last_part]
            return f"{city}, {state}, Australia"

        # Check if last part is a full state name
        for abbr, full in AU_STATES.items():
            if last_part.lower() == full.lower():
                city = " ".join(parts[:-1])
                return f"{city}, {full}, Australia"

    # Just append Australia if we can't parse it
    return f"{location}, Australia"


class SerpAPIError(Exception):
    """Base exception for SerpAPI errors."""
    pass


class AuthenticationError(SerpAPIError):
    """Invalid or missing API key."""
    pass


class RateLimitError(SerpAPIError):
    """API rate limit exceeded."""
    pass


class SerpAPIClient:
    """
    Client for SerpAPI Google Search endpoint.

    Usage:
        client = SerpAPIClient(api_key="your_key")
        results = client.search("buyer's agent", "Brisbane, QLD")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://serpapi.com/search",
        timeout: int = 30,
        google_domain: str = "google.com.au",
        gl: str = "au",
        hl: str = "en",
    ):
        """
        Initialize SerpAPI client.

        Args:
            api_key: SerpAPI API key (required)
            base_url: SerpAPI endpoint URL
            timeout: Request timeout in seconds
            google_domain: Google domain for localization
            gl: Geolocation (country code)
            hl: Language code
        """
        # Try environment variable if not provided
        if not api_key:
            import os
            api_key = os.environ.get("SERPAPI_KEY") or os.environ.get("PROSPECT_SERPAPI_KEY")

        if not api_key:
            raise AuthenticationError(
                "SerpAPI key not configured. "
                "Set SERPAPI_KEY environment variable or pass api_key parameter."
            )

        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.google_domain = google_domain
        self.gl = gl
        self.hl = hl

        self._client = httpx.Client(timeout=self.timeout)
        logger.debug("SerpAPI client initialized (domain=%s, gl=%s)", google_domain, gl)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(RateLimitError)
    )
    def search(
        self,
        business_type: str,
        location: str,
        num_results: int = 20
    ) -> SerpResults:
        """
        Search Google for businesses via SerpAPI.

        Args:
            business_type: Type of business (e.g., "buyer's agent")
            location: Location to search (e.g., "Brisbane, QLD")
            num_results: Maximum organic results to return

        Returns:
            SerpResults with ads, maps, and organic listings
        """
        # Normalize location for SerpAPI (handles Australian state abbreviations)
        normalized_location = normalize_au_location(location)
        query = f"{business_type} {location}"

        logger.debug("Location normalized: '%s' -> '%s'", location, normalized_location)

        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "location": normalized_location,
            "google_domain": self.google_domain,
            "gl": self.gl,
            "hl": self.hl,
            "num": min(num_results, 100),  # SerpAPI max
        }

        logger.info("SerpAPI search: %s", query)

        response = self._client.get(self.base_url, params=params)
        self._handle_errors(response)

        data = response.json()
        results = self._parse_response(data, query, location)

        logger.info(
            "SerpAPI returned: %d ads, %d maps, %d organic",
            len(results.ads),
            len(results.maps),
            len(results.organic),
        )

        return results

    def _handle_errors(self, response: httpx.Response) -> None:
        """Handle SerpAPI error responses."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid SerpAPI key")
        elif response.status_code == 429:
            raise RateLimitError("SerpAPI rate limit exceeded")
        elif response.status_code >= 500:
            raise SerpAPIError(f"SerpAPI server error: {response.status_code}")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", response.text)
            except Exception:
                error_msg = response.text
            raise SerpAPIError(f"SerpAPI error: {error_msg}")

    def _parse_response(
        self,
        data: dict,
        query: str,
        location: str
    ) -> SerpResults:
        """Parse SerpAPI JSON response into our models."""
        # Handle local_results which can be a dict with "places" key or a list
        local_results = data.get("local_results", {})
        if isinstance(local_results, dict):
            places = local_results.get("places", [])
        elif isinstance(local_results, list):
            places = local_results
        else:
            places = []

        return SerpResults(
            query=query,
            location=location,
            ads=self._parse_ads(data.get("ads", [])),
            maps=self._parse_local_results(places),
            organic=self._parse_organic(data.get("organic_results", [])),
        )

    def _parse_ads(self, ads_data: list) -> list[AdResult]:
        """Parse ad results from SerpAPI response."""
        results = []

        for ad in ads_data:
            try:
                results.append(AdResult(
                    position=ad.get("position", len(results) + 1),
                    headline=ad.get("title", ""),
                    display_url=ad.get("displayed_link", ""),
                    destination_url=ad.get("link", ""),
                    description=ad.get("description", ""),
                    is_top=ad.get("block_position", "").lower() == "top"
                ))
            except Exception as e:
                logger.debug("Failed to parse ad: %s", e)

        return results

    def _parse_local_results(self, places_data: list) -> list[MapsResult]:
        """Parse local/maps results from SerpAPI response."""
        results = []

        for i, place in enumerate(places_data):
            try:
                # Website can be in 'website' or 'links.website'
                website = place.get("website")
                if not website:
                    links = place.get("links", {})
                    if isinstance(links, dict):
                        website = links.get("website")

                results.append(MapsResult(
                    position=place.get("position", i + 1),
                    name=place.get("title", "Unknown"),
                    rating=place.get("rating"),
                    review_count=place.get("reviews"),
                    category=place.get("type"),
                    address=place.get("address", ""),
                    phone=place.get("phone"),
                    website=website
                ))
            except Exception as e:
                logger.debug("Failed to parse local result: %s", e)

        return results

    def _parse_organic(self, organic_data: list) -> list[OrganicResult]:
        """Parse organic results from SerpAPI response."""
        from ..dedup import normalize_domain
        results = []

        for item in organic_data:
            try:
                # Use normalize_domain for proper URL parsing
                url = item.get("link", "")
                domain = normalize_domain(url)

                if not domain:
                    logger.debug("Could not normalize domain from: %s", url)
                    continue

                # Skip directories
                if any(d in domain for d in DIRECTORY_DOMAINS):
                    continue

                results.append(OrganicResult(
                    position=item.get("position", len(results) + 1),
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    domain=domain,
                    snippet=item.get("snippet", "")
                ))
            except Exception as e:
                logger.debug("Failed to parse organic result: %s", e)

        return results

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
