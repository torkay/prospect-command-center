"""Deduplication logic for merging prospects from multiple sources."""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from .config import DIRECTORY_DOMAINS, DIRECTORY_URL_PATTERNS
from .models import Prospect, SerpResults, AdResult, MapsResult, OrganicResult
from .validation import (
    clean_business_name,
    validate_phone_for_location,
    filter_emails_for_domain,
)

logger = logging.getLogger(__name__)


def normalize_domain(url: str) -> Optional[str]:
    """
    Extract and normalize domain from URL.

    Args:
        url: Full URL or domain string

    Returns:
        Normalized domain without www prefix, or None if invalid

    Examples:
        "https://www.example.com/page" -> "example.com"
        "http://sub.example.com.au/" -> "sub.example.com.au"
        "example.com" -> "example.com"
        "not a url" -> None
        "https:" -> None
    """
    if not url:
        return None

    # Clean the URL string
    url = url.strip()

    # Reject obviously invalid inputs
    if url in ("https:", "http:", "https://", "http://"):
        return None

    try:
        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove any port number
        if ":" in domain:
            domain = domain.split(":")[0]

        # Validate it looks like a domain
        if not domain or "." not in domain or len(domain) < 4:
            return None

        # Check it doesn't contain invalid characters
        if any(c in domain for c in [" ", "<", ">", '"', "'", ";"]):
            return None

        return domain

    except Exception:
        return None


def normalize_name(name: str) -> str:
    """
    Normalize business name for comparison.

    Args:
        name: Business name

    Returns:
        Normalized name (lowercase, no special chars)
    """
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower()

    # Remove common suffixes
    suffixes = [
        "pty ltd",
        "pty. ltd.",
        "pty. ltd",
        "pty ltd.",
        "limited",
        "ltd",
        "inc",
        "llc",
        "corp",
        "co",
    ]
    for suffix in suffixes:
        normalized = re.sub(rf"\s+{re.escape(suffix)}\.?$", "", normalized)

    # Remove special characters except spaces
    normalized = re.sub(r"[^\w\s]", "", normalized)

    # Normalize whitespace
    normalized = " ".join(normalized.split())

    return normalized


def is_directory_url(url: str, domain: str) -> bool:
    """
    Check if URL/domain is a directory/aggregator site.

    Args:
        url: Full URL to check
        domain: Domain to check

    Returns:
        True if it's a directory site that should be filtered out
    """
    if not domain:
        return False

    domain_lower = domain.lower()

    # Check domain against blocklist using proper domain matching
    # Must be exact match OR end with .directory_domain (for subdomains)
    for dir_domain in DIRECTORY_DOMAINS:
        if domain_lower == dir_domain:
            return True
        if domain_lower.endswith('.' + dir_domain):
            return True

    # Check URL patterns (e.g., /r/ for Reddit, even if domain isn't blocked)
    if url:
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in DIRECTORY_URL_PATTERNS):
            return True

    return False


def is_directory_domain(domain: str) -> bool:
    """
    Check if domain is a directory/aggregator site.
    (Kept for backwards compatibility)

    Args:
        domain: Domain to check

    Returns:
        True if it's a directory site that should be filtered out
    """
    return is_directory_url("", domain)


def create_prospect_from_ad(ad: AdResult) -> Prospect:
    """Create a Prospect from an AdResult."""
    domain = normalize_domain(ad.destination_url)

    return Prospect(
        name=ad.headline,
        website=ad.destination_url,
        domain=domain,
        found_in_ads=True,
        ad_position=ad.position,
        source="ads",
    )


def create_prospect_from_maps(maps_result: MapsResult) -> Prospect:
    """Create a Prospect from a MapsResult."""
    domain = normalize_domain(maps_result.website) if maps_result.website else None

    return Prospect(
        name=maps_result.name,
        website=maps_result.website,
        domain=domain,
        phone=maps_result.phone,
        address=maps_result.address,
        found_in_maps=True,
        maps_position=maps_result.position,
        rating=maps_result.rating,
        review_count=maps_result.review_count,
        category=maps_result.category,
        source="maps",
    )


def create_prospect_from_organic(organic: OrganicResult) -> Prospect:
    """Create a Prospect from an OrganicResult."""
    return Prospect(
        name=organic.title,
        website=organic.url,
        domain=organic.domain,
        found_in_organic=True,
        organic_position=organic.position,
        source="organic",
    )


def merge_prospects(prospects: list[Prospect]) -> list[Prospect]:
    """
    Merge duplicate prospects based on domain and name similarity.

    Args:
        prospects: List of prospects to deduplicate

    Returns:
        Deduplicated list of prospects
    """
    # Index by domain
    domain_index: dict[str, Prospect] = {}
    # Index by normalized name (for prospects without domain)
    name_index: dict[str, Prospect] = {}
    # Final list for prospects that can't be matched
    unmatched: list[Prospect] = []

    for prospect in prospects:
        # Skip directory domains
        if prospect.domain and is_directory_domain(prospect.domain):
            logger.debug("Filtering out directory: %s", prospect.domain)
            continue

        merged = False

        # Try to match by domain first
        if prospect.domain:
            if prospect.domain in domain_index:
                domain_index[prospect.domain].merge_from(prospect)
                merged = True
            else:
                domain_index[prospect.domain] = prospect
                merged = True

        # Try to match by name if no domain match
        if not merged:
            normalized_name = normalize_name(prospect.name)
            if normalized_name:
                if normalized_name in name_index:
                    name_index[normalized_name].merge_from(prospect)
                else:
                    name_index[normalized_name] = prospect
            else:
                unmatched.append(prospect)

    # Combine all unique prospects
    result = list(domain_index.values())

    # Add name-indexed prospects that don't have domains
    for name, prospect in name_index.items():
        if not prospect.domain:
            result.append(prospect)

    result.extend(unmatched)

    logger.info(
        "Merged %d prospects down to %d unique entries",
        len(prospects),
        len(result),
    )

    return result


def deduplicate_serp_results(serp_results: SerpResults, location: str = "") -> list[Prospect]:
    """
    Convert SERP results to deduplicated prospect list.

    Priority order: Maps > Ads > Organic
    Maps results have the most reliable contact data.

    Args:
        serp_results: Raw SERP results containing ads, maps, and organic
        location: Search location for phone number validation

    Returns:
        Deduplicated list of Prospect objects
    """
    # Use domain as primary key for deduplication
    prospects_by_domain: dict[str, Prospect] = {}

    # Process maps results FIRST (highest quality contact data)
    for maps_result in serp_results.maps:
        domain = normalize_domain(maps_result.website) if maps_result.website else None

        # Skip directories
        if domain and is_directory_url(maps_result.website or "", domain):
            logger.debug("Filtering directory from maps: %s", domain)
            continue

        if domain:
            # Clean business name
            cleaned_name = clean_business_name(maps_result.name)

            # Validate phone for location
            phone = maps_result.phone
            if phone and location:
                is_valid, reason = validate_phone_for_location(phone, location)
                if not is_valid:
                    logger.debug("Filtering phone %s: %s", phone, reason)
                    phone = None

            prospects_by_domain[domain] = Prospect(
                name=cleaned_name,
                website=maps_result.website,
                domain=domain,
                phone=phone,
                address=maps_result.address,
                rating=maps_result.rating,
                review_count=maps_result.review_count,
                category=maps_result.category,
                found_in_maps=True,
                maps_position=maps_result.position,
                source="maps",
            )

    # Process ads (merge with existing or add new)
    for ad in serp_results.ads:
        domain = normalize_domain(ad.destination_url)

        # Skip directories
        if domain and is_directory_url(ad.destination_url, domain):
            logger.debug("Filtering directory from ads: %s", domain)
            continue

        if domain:
            if domain in prospects_by_domain:
                # Merge: add ad info
                prospects_by_domain[domain].found_in_ads = True
                prospects_by_domain[domain].ad_position = ad.position
            else:
                # Clean business name
                cleaned_name = clean_business_name(ad.headline)

                # New prospect from ad (NO phone/address - ads don't have this)
                prospects_by_domain[domain] = Prospect(
                    name=cleaned_name,
                    website=ad.destination_url,
                    domain=domain,
                    phone=None,
                    address=None,
                    found_in_ads=True,
                    ad_position=ad.position,
                    source="ads",
                )

    # Process organic results (merge with existing or add new)
    for organic in serp_results.organic:
        # Re-normalize domain from URL (don't trust organic.domain from SerpAPI)
        domain = normalize_domain(organic.url)

        # Skip if we can't get a valid domain
        if not domain:
            logger.debug("Skipping organic result with invalid domain: %s", organic.url)
            continue

        # Skip directories
        if is_directory_url(organic.url, domain):
            logger.debug("Filtering directory from organic: %s", domain)
            continue

        if domain in prospects_by_domain:
            # Merge: add organic info
            prospects_by_domain[domain].found_in_organic = True
            prospects_by_domain[domain].organic_position = organic.position
        else:
            # Clean business name
            cleaned_name = clean_business_name(organic.title)

            # New prospect from organic (NO phone/address - organic doesn't have this)
            prospects_by_domain[domain] = Prospect(
                name=cleaned_name,
                website=organic.url,
                domain=domain,
                phone=None,  # DO NOT set - organic results don't have phone
                address=None,  # DO NOT set - organic results don't have address
                found_in_organic=True,
                organic_position=organic.position,
                source="organic",
            )

    result = list(prospects_by_domain.values())

    logger.info(
        "Deduplicated to %d unique prospects from %d ads, %d maps, %d organic",
        len(result),
        len(serp_results.ads),
        len(serp_results.maps),
        len(serp_results.organic),
    )

    return result
