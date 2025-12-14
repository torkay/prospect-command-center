"""Opportunity score calculation - Do they need marketing help?"""

from typing import Optional
from ..config import ScoringConfig
from ..models import Prospect, WebsiteSignals


def calculate_opportunity_score(
    prospect: Prospect,
    config: Optional[ScoringConfig] = None,
) -> int:
    """
    Calculate the opportunity score for a prospect.

    Opportunity score represents how much they could benefit from marketing services.
    Higher score = more gaps in their current marketing = better opportunity.

    Args:
        prospect: The prospect to score
        config: Scoring configuration (uses defaults if not provided)

    Returns:
        Opportunity score from 0-100
    """
    config = config or ScoringConfig()
    score = 0

    # No website is a huge opportunity
    if not prospect.website:
        return 80

    signals = prospect.signals
    if not signals:
        # Can't analyse, assume moderate opportunity
        return 50

    # Missing Google Analytics (15 points) - only if confirmed absent
    if signals.has_google_analytics is False:
        score += config.no_analytics_weight

    # Missing Facebook Pixel (10 points) - only if confirmed absent
    if signals.has_facebook_pixel is False:
        score += config.no_pixel_weight

    # No booking system (15 points) - only if confirmed absent
    if signals.has_booking_system is False:
        score += config.no_booking_weight

    # No contact emails on site (10 points)
    if not signals.emails:
        score += config.no_contact_weight

    # Using a "weak" CMS (10 points)
    weak_cms = ["Wix", "Weebly", "GoDaddy Website Builder"]
    if signals.cms and signals.cms in weak_cms:
        score += config.weak_cms_weight

    # Slow site (10 points) - over 3 seconds
    if signals.load_time_ms and signals.load_time_ms > 3000:
        score += config.slow_site_weight

    # PENALTIES for strong marketing presence

    # Already running ads (they know about marketing)
    if prospect.found_in_ads:
        score += config.running_ads_penalty  # Negative value

    # Has both GA and FB pixel (sophisticated) - only if confirmed present
    if signals.has_google_analytics is True and signals.has_facebook_pixel is True:
        score += config.good_tracking_penalty  # Negative value

    # BONUSES for poor search visibility

    # Poor Maps ranking (position > 1)
    if prospect.found_in_maps and prospect.maps_position and prospect.maps_position > 1:
        score += config.poor_maps_ranking_weight

    # Poor or no organic ranking
    if not prospect.found_in_organic:
        score += config.poor_organic_ranking_weight
    elif prospect.organic_position and prospect.organic_position > 5:
        score += config.poor_organic_ranking_weight

    # Clamp to 0-100
    return max(0, min(score, 100))


def get_opportunity_breakdown(prospect: Prospect) -> dict:
    """
    Get a detailed breakdown of opportunity score components.

    Args:
        prospect: The prospect to analyze

    Returns:
        Dictionary with score components and explanations
    """
    config = ScoringConfig()
    breakdown = {
        "total": 0,
        "opportunities": [],
        "strengths": [],
    }

    if not prospect.website:
        breakdown["opportunities"].append({
            "factor": "No website",
            "points": 80,
            "note": "Huge opportunity - they need a web presence",
        })
        breakdown["total"] = 80
        return breakdown

    signals = prospect.signals
    if not signals:
        breakdown["opportunities"].append({
            "factor": "Unable to analyse website",
            "points": 50,
            "note": "Website was unreachable during analysis; technical details unknown",
        })
        breakdown["total"] = 50
        return breakdown

    # Opportunities (positive points) - only if confirmed absent, not unknown
    if signals.has_google_analytics is False:
        breakdown["opportunities"].append({
            "factor": "No Google Analytics",
            "points": config.no_analytics_weight,
            "note": "Not tracking website performance",
        })
        breakdown["total"] += config.no_analytics_weight

    if signals.has_facebook_pixel is False:
        breakdown["opportunities"].append({
            "factor": "No Facebook Pixel",
            "points": config.no_pixel_weight,
            "note": "Missing retargeting opportunity",
        })
        breakdown["total"] += config.no_pixel_weight

    if signals.has_booking_system is False:
        breakdown["opportunities"].append({
            "factor": "No booking system",
            "points": config.no_booking_weight,
            "note": "Could benefit from online scheduling",
        })
        breakdown["total"] += config.no_booking_weight

    if not signals.emails:
        breakdown["opportunities"].append({
            "factor": "No visible email",
            "points": config.no_contact_weight,
            "note": "Contact info not easily found",
        })
        breakdown["total"] += config.no_contact_weight

    weak_cms = ["Wix", "Weebly", "GoDaddy Website Builder"]
    if signals.cms and signals.cms in weak_cms:
        breakdown["opportunities"].append({
            "factor": f"Using {signals.cms}",
            "points": config.weak_cms_weight,
            "note": "Limited platform - may benefit from upgrade",
        })
        breakdown["total"] += config.weak_cms_weight

    if signals.load_time_ms and signals.load_time_ms > 3000:
        breakdown["opportunities"].append({
            "factor": f"Slow website ({signals.load_time_ms}ms)",
            "points": config.slow_site_weight,
            "note": "Page speed affects SEO and conversions",
        })
        breakdown["total"] += config.slow_site_weight

    if not prospect.found_in_organic:
        breakdown["opportunities"].append({
            "factor": "Not ranking in organic results",
            "points": config.poor_organic_ranking_weight,
            "note": "Missing out on free search traffic",
        })
        breakdown["total"] += config.poor_organic_ranking_weight
    elif prospect.organic_position and prospect.organic_position > 5:
        breakdown["opportunities"].append({
            "factor": f"Low organic ranking (position {prospect.organic_position})",
            "points": config.poor_organic_ranking_weight,
            "note": "Could improve search visibility",
        })
        breakdown["total"] += config.poor_organic_ranking_weight

    if prospect.found_in_maps and prospect.maps_position and prospect.maps_position > 1:
        breakdown["opportunities"].append({
            "factor": f"Not #1 in Maps (position {prospect.maps_position})",
            "points": config.poor_maps_ranking_weight,
            "note": "Room to improve local visibility",
        })
        breakdown["total"] += config.poor_maps_ranking_weight

    # Strengths (negative points / penalties)
    if prospect.found_in_ads:
        breakdown["strengths"].append({
            "factor": "Already running Google Ads",
            "points": abs(config.running_ads_penalty),
            "note": "Shows marketing awareness",
        })
        breakdown["total"] += config.running_ads_penalty

    if signals.has_google_analytics is True and signals.has_facebook_pixel is True:
        breakdown["strengths"].append({
            "factor": "Has both GA and FB tracking",
            "points": abs(config.good_tracking_penalty),
            "note": "Sophisticated marketing setup",
        })
        breakdown["total"] += config.good_tracking_penalty

    breakdown["total"] = max(0, min(breakdown["total"], 100))
    return breakdown
