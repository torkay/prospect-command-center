"""Technology detection (CMS, tracking, booking systems)."""

from typing import Optional, Dict

from ..config import CMS_SIGNATURES, TRACKING_SIGNATURES, BOOKING_SIGNATURES


def detect_cms(html: str) -> Optional[str]:
    """
    Detect the CMS/website builder used.

    Args:
        html: Raw HTML content

    Returns:
        CMS name if detected, None otherwise
    """
    if not html:
        return None

    html_lower = html.lower()

    for cms_name, signatures in CMS_SIGNATURES.items():
        for signature in signatures:
            if signature.lower() in html_lower:
                return cms_name

    return None


def detect_tracking(html: str) -> Dict[str, bool]:
    """
    Detect tracking pixels and analytics tools.

    Args:
        html: Raw HTML content

    Returns:
        Dictionary with tracking tool detection results
    """
    result = {
        "google_analytics": False,
        "facebook_pixel": False,
        "google_ads": False,
    }

    if not html:
        return result

    html_lower = html.lower()

    for tracker, signatures in TRACKING_SIGNATURES.items():
        for signature in signatures:
            if signature.lower() in html_lower:
                result[tracker] = True
                break

    return result


def detect_booking_system(html: str) -> bool:
    """
    Detect if the website has a booking/scheduling system.

    Args:
        html: Raw HTML content

    Returns:
        True if booking system detected, False otherwise
    """
    if not html:
        return False

    html_lower = html.lower()

    for signature in BOOKING_SIGNATURES:
        if signature.lower() in html_lower:
            return True

    return False


def analyze_tech_stack(html: str) -> dict:
    """
    Perform comprehensive tech stack analysis.

    Args:
        html: Raw HTML content

    Returns:
        Dictionary with all detected technologies
    """
    result = {
        "cms": detect_cms(html),
        "tracking": detect_tracking(html),
        "has_booking": detect_booking_system(html),
        "frameworks": detect_frameworks(html),
        "has_ssl": False,  # Would need to check URL
        "has_responsive": detect_responsive(html),
    }

    return result


def detect_frameworks(html: str) -> list[str]:
    """
    Detect JavaScript frameworks and libraries.

    Args:
        html: Raw HTML content

    Returns:
        List of detected frameworks
    """
    frameworks = []

    if not html:
        return frameworks

    html_lower = html.lower()

    framework_signatures = {
        "React": ["react", "reactdom", "__react"],
        "Vue.js": ["vue.js", "vuejs", "__vue__"],
        "Angular": ["ng-app", "ng-controller", "angular"],
        "jQuery": ["jquery", "$(document)", "$.ajax"],
        "Bootstrap": ["bootstrap.min", "bootstrap.css"],
        "Tailwind": ["tailwindcss", "tailwind.css"],
    }

    for framework, signatures in framework_signatures.items():
        for signature in signatures:
            if signature in html_lower:
                frameworks.append(framework)
                break

    return frameworks


def detect_responsive(html: str) -> bool:
    """
    Check if website appears to be responsive/mobile-friendly.

    Args:
        html: Raw HTML content

    Returns:
        True if responsive indicators found
    """
    if not html:
        return False

    html_lower = html.lower()

    responsive_indicators = [
        'viewport',
        'media=',
        '@media',
        'responsive',
        'mobile',
        'bootstrap',
        'tailwind',
    ]

    return any(indicator in html_lower for indicator in responsive_indicators)


def get_cms_quality_tier(cms: Optional[str]) -> str:
    """
    Categorize CMS by quality/professionalism tier.

    Args:
        cms: CMS name

    Returns:
        Quality tier: "premium", "standard", "basic", or "unknown"
    """
    if not cms:
        return "unknown"

    cms_lower = cms.lower()

    premium_cms = ["wordpress", "shopify", "webflow"]
    standard_cms = ["squarespace", "joomla", "drupal"]
    basic_cms = ["wix", "weebly", "godaddy"]

    if any(p in cms_lower for p in premium_cms):
        return "premium"
    elif any(s in cms_lower for s in standard_cms):
        return "standard"
    elif any(b in cms_lower for b in basic_cms):
        return "basic"

    return "unknown"
