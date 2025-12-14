"""Generate plain-English opportunity notes for prospects."""

from ..models import Prospect, WebsiteSignals


def generate_opportunity_notes(prospect: Prospect) -> str:
    """
    Generate plain-English notes describing marketing opportunities.

    Args:
        prospect: The prospect to analyze

    Returns:
        Human-readable string describing opportunities
    """
    notes = []

    # No website - major opportunity
    if not prospect.website:
        notes.append("No website found - needs web presence")
        if prospect.found_in_maps:
            notes.append("Has Google Business Profile but no site to drive traffic to")
        return "; ".join(notes)

    signals = prospect.signals
    if not signals or not signals.reachable:
        notes.append("Website was unreachable during analysis; technical details unknown")
        return "; ".join(notes)

    # Categorize opportunities by type
    seo_opportunities = []
    tracking_opportunities = []
    conversion_opportunities = []
    technical_opportunities = []

    # SEO opportunities
    if not prospect.found_in_organic:
        seo_opportunities.append("not ranking in organic search")
    elif prospect.organic_position and prospect.organic_position > 5:
        seo_opportunities.append(f"ranking #{prospect.organic_position} in organic (room to improve)")

    if prospect.found_in_maps and prospect.maps_position and prospect.maps_position > 1:
        seo_opportunities.append(f"#{prospect.maps_position} in local pack (not #1)")

    # Tracking opportunities - only if confirmed absent, not unknown
    if signals.has_google_analytics is False:
        tracking_opportunities.append("no Google Analytics")
    if signals.has_facebook_pixel is False:
        tracking_opportunities.append("no Facebook Pixel")

    # Conversion opportunities - only if confirmed absent
    if signals.has_booking_system is False:
        conversion_opportunities.append("no online booking")
    if not signals.emails:
        conversion_opportunities.append("no visible contact email")
    if not prospect.phone:
        conversion_opportunities.append("phone not easily found")

    # Technical opportunities
    weak_cms = ["Wix", "Weebly", "GoDaddy Website Builder"]
    if signals.cms and signals.cms in weak_cms:
        technical_opportunities.append(f"using {signals.cms} (limited platform)")

    if signals.load_time_ms and signals.load_time_ms > 3000:
        technical_opportunities.append(f"slow site ({signals.load_time_ms}ms load time)")

    # Build notes string
    if seo_opportunities:
        notes.append("SEO: " + ", ".join(seo_opportunities))

    if tracking_opportunities:
        notes.append("Tracking: " + ", ".join(tracking_opportunities))

    if conversion_opportunities:
        notes.append("Conversion: " + ", ".join(conversion_opportunities))

    if technical_opportunities:
        notes.append("Technical: " + ", ".join(technical_opportunities))

    # Add positive signals as context
    strengths = []
    if prospect.found_in_ads:
        strengths.append("already running ads")
    if signals.has_google_analytics is True and signals.has_facebook_pixel is True:
        strengths.append("has good tracking setup")
    if prospect.rating and prospect.rating >= 4.5:
        strengths.append(f"excellent reviews ({prospect.rating}★)")

    if strengths:
        notes.append("Note: " + ", ".join(strengths))

    if not notes:
        notes.append("Well-optimized - limited obvious opportunities")

    return "; ".join(notes)


def generate_outreach_angle(prospect: Prospect) -> str:
    """
    Generate a suggested outreach angle based on opportunities.

    Args:
        prospect: The prospect to analyze

    Returns:
        Suggested outreach angle/talking point
    """
    if not prospect.website:
        return "Offer to build their first website and establish online presence"

    signals = prospect.signals
    if not signals or not signals.reachable:
        return "Website may have technical issues - offer a website audit"

    # Determine primary angle based on biggest opportunity
    if not prospect.found_in_organic and not prospect.found_in_maps:
        return "Help them get found online - currently invisible in search"

    if signals.has_google_analytics is False and signals.has_facebook_pixel is False:
        return "Help them understand their website traffic and customer behaviour"

    if signals.has_booking_system is False:
        return "Streamline their booking process with online scheduling"

    if prospect.found_in_maps and prospect.maps_position and prospect.maps_position > 1:
        return f"Help them reach #1 in local search (currently #{prospect.maps_position})"

    if signals.cms in ["Wix", "Weebly", "GoDaddy Website Builder"]:
        return "Upgrade their website platform for better performance and SEO"

    if signals.load_time_ms and signals.load_time_ms > 3000:
        return "Speed up their website to improve user experience and SEO"

    return "General marketing consultation - assess specific needs"


def get_priority_services(prospect: Prospect) -> list[str]:
    """
    Get a prioritized list of services that could help this prospect.

    Args:
        prospect: The prospect to analyze

    Returns:
        List of services in priority order
    """
    services = []

    if not prospect.website:
        services.append("Website Development")
        services.append("Google Business Profile Setup")
        return services

    signals = prospect.signals
    if not signals:
        services.append("Website Audit")
        return services

    # SEO services
    if not prospect.found_in_organic or (prospect.organic_position and prospect.organic_position > 5):
        services.append("SEO")

    # Local SEO
    if not prospect.found_in_maps or (prospect.maps_position and prospect.maps_position > 1):
        services.append("Local SEO")

    # PPC (if not already running ads)
    if not prospect.found_in_ads:
        services.append("Google Ads")

    # Tracking setup - only if confirmed absent
    if signals.has_google_analytics is False:
        services.append("Analytics Setup")
    if signals.has_facebook_pixel is False:
        services.append("Facebook Ads / Retargeting")

    # Conversion optimisation - only if confirmed absent
    if signals.has_booking_system is False:
        services.append("Booking System")

    # Website improvements
    weak_cms = ["Wix", "Weebly", "GoDaddy Website Builder"]
    if signals.cms and signals.cms in weak_cms:
        services.append("Website Redesign")
    elif signals.load_time_ms and signals.load_time_ms > 3000:
        services.append("Website Optimization")

    return services[:5]  # Return top 5 services
