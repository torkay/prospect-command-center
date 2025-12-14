"""Search query building utilities."""

from typing import Optional
from urllib.parse import quote_plus


def build_search_query(
    business_type: str,
    location: str,
    modifier: Optional[str] = None,
) -> str:
    """
    Build a Google search query for local business discovery.

    Args:
        business_type: Type of business (e.g., "buyer's agent")
        location: Location to search (e.g., "Brisbane, QLD")
        modifier: Optional search modifier (e.g., "best", "top")

    Returns:
        Formatted search query string
    """
    parts = []

    if modifier:
        parts.append(modifier)

    parts.append(business_type)
    parts.append(location)

    return " ".join(parts)


def build_google_url(query: str, start: int = 0) -> str:
    """
    Build a Google search URL.

    Args:
        query: Search query string
        start: Result offset (for pagination)

    Returns:
        Full Google search URL
    """
    encoded_query = quote_plus(query)
    base_url = "https://www.google.com.au/search"

    params = [
        f"q={encoded_query}",
        "hl=en",
        "gl=au",
        "num=20",  # Request more results
    ]

    if start > 0:
        params.append(f"start={start}")

    return f"{base_url}?{'&'.join(params)}"


def get_query_variations(business_type: str, location: str) -> list[str]:
    """
    Generate query variations to maximize coverage.

    Args:
        business_type: Type of business
        location: Location to search

    Returns:
        List of query variations
    """
    variations = [
        build_search_query(business_type, location),
        build_search_query(business_type, location, "best"),
        build_search_query(business_type, location, "top"),
        build_search_query(f"{business_type} near me", location),
    ]

    return variations
