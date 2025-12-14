"""Fit score calculation - Can we reach this prospect?"""

from typing import Optional
from ..config import ScoringConfig
from ..models import Prospect


def calculate_fit_score(
    prospect: Prospect,
    config: Optional[ScoringConfig] = None,
) -> int:
    """
    Calculate the fit score for a prospect.

    Fit score represents how reachable/contactable the prospect is.
    Higher score = easier to contact and establish a relationship.

    Args:
        prospect: The prospect to score
        config: Scoring configuration (uses defaults if not provided)

    Returns:
        Fit score from 0-100
    """
    config = config or ScoringConfig()
    score = 0

    # Has a website (15 points)
    if prospect.website:
        score += config.website_weight

    # Has a phone number (15 points)
    if prospect.phone:
        score += config.phone_weight

    # Has email addresses (10 points)
    if prospect.emails:
        score += config.email_weight

    # Found in Google Maps (15 points)
    if prospect.found_in_maps:
        score += config.maps_presence_weight

    # Good rating (10 points) - 4.0+
    if prospect.rating and prospect.rating >= 4.0:
        score += config.good_rating_weight

    # Has reviews (10 points) - 10+
    if prospect.review_count and prospect.review_count >= 10:
        score += config.review_count_weight

    # Running ads (10 points) - shows they invest in marketing
    if prospect.found_in_ads:
        score += config.ads_presence_weight

    # Ranks in organic top 10 (15 points)
    if prospect.found_in_organic and prospect.organic_position and prospect.organic_position <= 10:
        score += config.organic_top10_weight

    # Cap at 100
    return min(score, 100)


def get_fit_breakdown(prospect: Prospect) -> dict:
    """
    Get a detailed breakdown of fit score components.

    Args:
        prospect: The prospect to analyze

    Returns:
        Dictionary with score components and explanations
    """
    config = ScoringConfig()
    breakdown = {
        "total": 0,
        "components": [],
    }

    if prospect.website:
        breakdown["components"].append({
            "factor": "Has website",
            "points": config.website_weight,
        })
        breakdown["total"] += config.website_weight

    if prospect.phone:
        breakdown["components"].append({
            "factor": "Has phone number",
            "points": config.phone_weight,
        })
        breakdown["total"] += config.phone_weight

    if prospect.emails:
        breakdown["components"].append({
            "factor": f"Has {len(prospect.emails)} email(s)",
            "points": config.email_weight,
        })
        breakdown["total"] += config.email_weight

    if prospect.found_in_maps:
        breakdown["components"].append({
            "factor": f"Found in Google Maps (position {prospect.maps_position})",
            "points": config.maps_presence_weight,
        })
        breakdown["total"] += config.maps_presence_weight

    if prospect.rating and prospect.rating >= 4.0:
        breakdown["components"].append({
            "factor": f"Good rating ({prospect.rating}★)",
            "points": config.good_rating_weight,
        })
        breakdown["total"] += config.good_rating_weight

    if prospect.review_count and prospect.review_count >= 10:
        breakdown["components"].append({
            "factor": f"Has reviews ({prospect.review_count})",
            "points": config.review_count_weight,
        })
        breakdown["total"] += config.review_count_weight

    if prospect.found_in_ads:
        breakdown["components"].append({
            "factor": f"Running Google Ads (position {prospect.ad_position})",
            "points": config.ads_presence_weight,
        })
        breakdown["total"] += config.ads_presence_weight

    if prospect.found_in_organic and prospect.organic_position and prospect.organic_position <= 10:
        breakdown["components"].append({
            "factor": f"Organic top 10 (position {prospect.organic_position})",
            "points": config.organic_top10_weight,
        })
        breakdown["total"] += config.organic_top10_weight

    breakdown["total"] = min(breakdown["total"], 100)
    return breakdown
