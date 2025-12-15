"""
Programmatic API for the Prospect Command Center.

Usage:
    from prospect import search_prospects

    results = search_prospects("plumber", "Sydney")
    high_priority = [r for r in results if r.priority_score > 60]
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, List

from prospect.config import Settings, load_config, ScraperConfig
from prospect.scraper import SerpAPIClient, AuthenticationError
from prospect.dedup import deduplicate_serp_results
from prospect.enrichment.crawler import WebsiteCrawler
from prospect.scoring import (
    calculate_fit_score,
    calculate_opportunity_score,
    generate_opportunity_notes,
)
from prospect.models import Prospect

logger = logging.getLogger(__name__)


@dataclass
class ProspectResult:
    """Simplified result for library usage."""

    name: str
    domain: str
    website: str
    phone: str
    emails: list
    address: str
    rating: float
    reviews: int
    fit_score: int
    opportunity_score: int
    priority_score: float
    opportunity_notes: str
    source: str  # 'ads', 'maps', 'organic', or combination
    raw: Optional[Prospect] = None  # Original prospect for advanced use

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "domain": self.domain,
            "website": self.website,
            "phone": self.phone,
            "emails": self.emails,
            "address": self.address,
            "rating": self.rating,
            "reviews": self.reviews,
            "fit_score": self.fit_score,
            "opportunity_score": self.opportunity_score,
            "priority_score": round(self.priority_score, 2),
            "opportunity_notes": self.opportunity_notes,
            "source": self.source,
        }


def search_prospects(
    business_type: str,
    location: str,
    limit: int = 20,
    skip_enrichment: bool = False,
    min_fit: int = 0,
    min_opportunity: int = 0,
    min_priority: float = 0,
    config_path: Optional[str] = None,
    fit_weight: float = 0.4,
    opportunity_weight: float = 0.6,
) -> List[ProspectResult]:
    """
    Search for prospects matching criteria.

    Args:
        business_type: Type of business (e.g., "plumber")
        location: Location to search (e.g., "Sydney, NSW")
        limit: Maximum number of results
        skip_enrichment: Skip website analysis for speed
        min_fit: Minimum fit score filter
        min_opportunity: Minimum opportunity score filter
        min_priority: Minimum priority score filter
        config_path: Optional path to YAML config
        fit_weight: Weight for fit score in priority (0-1)
        opportunity_weight: Weight for opportunity score in priority (0-1)

    Returns:
        List of ProspectResult objects, sorted by priority_score

    Example:
        results = search_prospects("accountant", "Melbourne", limit=10)
        for r in results:
            if r.priority_score > 60:
                print(f"High priority: {r.name} ({r.phone})")
    """
    settings = load_config(config_path) if config_path else Settings()
    settings.fit_weight = fit_weight
    settings.opportunity_weight = opportunity_weight

    # Search via SerpAPI
    try:
        client = SerpAPIClient()
        serp_results = client.search(business_type, location, limit)
        client.close()
    except AuthenticationError as e:
        raise RuntimeError(f"SerpAPI not configured: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Search failed: {e}") from e

    # Deduplicate (pass location for phone validation)
    prospects = deduplicate_serp_results(serp_results, location=location)

    if not prospects:
        return []

    # Enrich
    if not skip_enrichment:
        config = ScraperConfig()

        async def enrich_all():
            async with WebsiteCrawler(config) as crawler:
                for prospect in prospects:
                    try:
                        await crawler.enrich_prospect(prospect)
                    except Exception as e:
                        logger.debug("Failed to enrich %s: %s", prospect.name, e)

        asyncio.run(enrich_all())

    # Score
    for prospect in prospects:
        prospect.fit_score = calculate_fit_score(prospect)
        prospect.opportunity_score = calculate_opportunity_score(prospect)
        prospect.priority_score = (
            prospect.fit_score * fit_weight +
            prospect.opportunity_score * opportunity_weight
        )
        prospect.opportunity_notes = generate_opportunity_notes(prospect)

    # Sort by priority
    prospects.sort(key=lambda p: p.priority_score, reverse=True)

    # Convert to ProspectResult
    results = []
    for p in prospects:
        # Determine source
        sources = []
        if p.found_in_ads:
            sources.append("ads")
        if p.found_in_maps:
            sources.append("maps")
        if p.found_in_organic:
            sources.append("organic")

        result = ProspectResult(
            name=p.name or "",
            domain=p.domain or "",
            website=p.website or "",
            phone=p.phone or "",
            emails=p.emails or [],
            address=p.address or "",
            rating=p.rating or 0,
            reviews=p.review_count or 0,
            fit_score=p.fit_score,
            opportunity_score=p.opportunity_score,
            priority_score=p.priority_score,
            opportunity_notes=p.opportunity_notes or "",
            source="+".join(sources) if sources else "unknown",
            raw=p,
        )
        results.append(result)

    # Apply filters
    if min_fit:
        results = [r for r in results if r.fit_score >= min_fit]
    if min_opportunity:
        results = [r for r in results if r.opportunity_score >= min_opportunity]
    if min_priority:
        results = [r for r in results if r.priority_score >= min_priority]

    return results[:limit]
