"""Data validation utilities for phone, email, and business name cleaning."""

import re
from typing import Optional, Tuple

# Australian phone area codes by state
AU_AREA_CODES = {
    # State: (landline_prefix, description)
    "QLD": ("07", "Queensland"),
    "NSW": ("02", "New South Wales"),
    "VIC": ("03", "Victoria"),
    "SA": ("08", "South Australia"),
    "WA": ("08", "Western Australia"),
    "TAS": ("03", "Tasmania"),
    "NT": ("08", "Northern Territory"),
    "ACT": ("02", "Australian Capital Territory"),
}

# Location keywords to state mapping
LOCATION_TO_STATE = {
    # QLD
    "brisbane": "QLD",
    "gold coast": "QLD",
    "sunshine coast": "QLD",
    "cairns": "QLD",
    "townsville": "QLD",
    "toowoomba": "QLD",
    "rockhampton": "QLD",
    "mackay": "QLD",
    "bundaberg": "QLD",
    "hervey bay": "QLD",
    "gladstone": "QLD",
    "qld": "QLD",
    "queensland": "QLD",
    # NSW
    "sydney": "NSW",
    "newcastle": "NSW",
    "wollongong": "NSW",
    "central coast": "NSW",
    "coffs harbour": "NSW",
    "tamworth": "NSW",
    "wagga wagga": "NSW",
    "albury": "NSW",
    "port macquarie": "NSW",
    "nsw": "NSW",
    "new south wales": "NSW",
    # VIC
    "melbourne": "VIC",
    "geelong": "VIC",
    "ballarat": "VIC",
    "bendigo": "VIC",
    "shepparton": "VIC",
    "mildura": "VIC",
    "warrnambool": "VIC",
    "vic": "VIC",
    "victoria": "VIC",
    # SA
    "adelaide": "SA",
    "mount gambier": "SA",
    "whyalla": "SA",
    "murray bridge": "SA",
    "port augusta": "SA",
    "sa": "SA",
    "south australia": "SA",
    # WA
    "perth": "WA",
    "fremantle": "WA",
    "mandurah": "WA",
    "bunbury": "WA",
    "geraldton": "WA",
    "kalgoorlie": "WA",
    "albany": "WA",
    "wa": "WA",
    "western australia": "WA",
    # TAS
    "hobart": "TAS",
    "launceston": "TAS",
    "devonport": "TAS",
    "burnie": "TAS",
    "tas": "TAS",
    "tasmania": "TAS",
    # NT
    "darwin": "NT",
    "alice springs": "NT",
    "katherine": "NT",
    "nt": "NT",
    "northern territory": "NT",
    # ACT
    "canberra": "ACT",
    "act": "ACT",
    "australian capital territory": "ACT",
}


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number format.

    Args:
        phone: Raw phone number string

    Returns:
        Normalized phone number with only digits, or empty string
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    digits = re.sub(r'[^\d+]', '', phone)

    # Handle Australian format
    if digits.startswith('+61'):
        digits = '0' + digits[3:]
    elif digits.startswith('61') and len(digits) > 10:
        digits = '0' + digits[2:]

    return digits


def get_state_from_location(location: str) -> Optional[str]:
    """
    Extract state from location string.

    Args:
        location: Location string (e.g., "Brisbane, QLD")

    Returns:
        State code (e.g., "QLD") or None if not found
    """
    if not location:
        return None

    location_lower = location.lower()

    for keyword, state in LOCATION_TO_STATE.items():
        if keyword in location_lower:
            return state

    return None


def validate_phone_for_location(phone: str, location: str) -> Tuple[bool, str]:
    """
    Validate that a phone number matches the expected area code for a location.

    Args:
        phone: Phone number to validate
        location: Location string to determine expected area code

    Returns:
        Tuple of (is_valid, reason)
    """
    if not phone:
        return True, "No phone"

    normalized = normalize_phone(phone)
    if not normalized:
        return False, "Invalid format"

    # Mobile numbers (04xx) are valid anywhere
    if normalized.startswith('04'):
        return True, "Mobile"

    # Toll-free numbers are valid anywhere
    if normalized.startswith('1300') or normalized.startswith('1800') or normalized.startswith('13'):
        return True, "Toll-free"

    # Get expected state
    state = get_state_from_location(location)
    if not state:
        return True, "Unknown location"  # Can't validate

    # Check landline prefix
    expected_prefix = AU_AREA_CODES.get(state, (None, ""))[0]
    if expected_prefix and normalized.startswith(expected_prefix):
        return True, f"Valid {state} landline"

    # Wrong area code
    if normalized[:2] in ['02', '03', '07', '08']:
        actual_prefix = normalized[:2]
        # Find which state this prefix belongs to
        for s, (prefix, _) in AU_AREA_CODES.items():
            if prefix == actual_prefix:
                return False, f"Area code {actual_prefix} is for {s}, not {state}"
        return False, f"Wrong area code for {state}"

    return True, "Unknown format"


def clean_business_name(name: str) -> str:
    """
    Clean up business name from Google SERP titles.

    Removes:
    - Everything after | or :
    - Star emojis and review counts
    - Marketing fluff

    Args:
        name: Raw business name from SERP

    Returns:
        Cleaned business name
    """
    if not name:
        return ""

    # Remove star emojis and variations
    name = re.sub(r'[\u2B50\u2605\u2606\u2729\u272A\u2730\U0001F31F]+', '', name)

    # Remove review counts like "2.2K+ Reviews", "(500+ reviews)"
    name = re.sub(r'\d+\.?\d*[Kk]?\+?\s*reviews?', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\(\d+\.?\d*[Kk]?\+?\s*reviews?\)', '', name, flags=re.IGNORECASE)

    # Cut at | or - or : (keeping first part)
    for delimiter in [' | ', ' - ', ': ']:
        if delimiter in name:
            name = name.split(delimiter)[0]

    # Remove common marketing suffixes
    suffixes_to_remove = [
        r'\s*-\s*local\s*&\s*reliable.*',
        r'\s*-\s*trusted.*',
        r'\s*-\s*best\s*reviewed.*',
        r'\s*-\s*same[- ]?day.*',
        r'\s*\d+\+?\s*local.*',
        r'\s*-\s*#1\s*rated.*',
        r'\s*-\s*fast\s*&\s*reliable.*',
        r'\s*-\s*affordable.*',
        r'\s*-\s*professional.*',
        r'\s*-\s*expert.*',
        r'\s*-\s*your\s*local.*',
        r'\s*-\s*licensed\s*&\s*insured.*',
        r'\s*-\s*24/7.*',
        r'\s*-\s*free\s*quotes?.*',
    ]
    for pattern in suffixes_to_remove:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Clean up whitespace
    name = ' '.join(name.split())

    return name.strip()


def validate_email_domain(email: str, website_domain: str) -> Tuple[bool, str]:
    """
    Check if email domain matches or is related to the website domain.

    Catches cross-contamination like billy@bkc.media on fallonsolutions.com.au

    Args:
        email: Email address to validate
        website_domain: Domain of the business website

    Returns:
        Tuple of (is_valid, reason)
    """
    if not email or not website_domain:
        return True, "No email or domain"

    email_domain = email.split('@')[-1].lower() if '@' in email else ''
    website_domain = website_domain.lower().replace('www.', '')

    if not email_domain:
        return True, "Invalid email format"

    # Exact match
    if email_domain == website_domain:
        return True, "Exact match"

    # Allow subdomains
    if email_domain.endswith('.' + website_domain):
        return True, "Subdomain"

    # Allow parent domain
    if website_domain.endswith('.' + email_domain):
        return True, "Parent domain"

    # Allow same base domain (e.g., example.com.au and mail.example.com.au)
    # Extract base domain parts
    email_parts = email_domain.split('.')
    website_parts = website_domain.split('.')

    # Get the main domain (last 2-3 parts depending on TLD)
    def get_base_domain(parts):
        if len(parts) >= 3 and parts[-2] in ['com', 'net', 'org', 'gov', 'edu']:
            return '.'.join(parts[-3:])
        elif len(parts) >= 2:
            return '.'.join(parts[-2:])
        return '.'.join(parts)

    if get_base_domain(email_parts) == get_base_domain(website_parts):
        return True, "Same base domain"

    # Common email providers are okay but noted as generic
    generic_providers = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'live.com', 'icloud.com', 'me.com', 'aol.com',
        'mail.com', 'protonmail.com', 'zoho.com',
        'bigpond.com', 'bigpond.net.au', 'optusnet.com.au',
        'telstra.com', 'tpg.com.au', 'internode.on.net',
    ]
    if email_domain in generic_providers:
        return True, "Generic provider"

    # Mismatch - likely cross-contamination
    return False, f"Domain mismatch: {email_domain} vs {website_domain}"


def filter_emails_for_domain(emails: list, website_domain: str) -> list:
    """
    Filter a list of emails to only include those that match the website domain.

    Args:
        emails: List of email addresses
        website_domain: Domain of the business website

    Returns:
        Filtered list of valid emails
    """
    if not emails:
        return []

    valid_emails = []
    for email in emails:
        is_valid, _ = validate_email_domain(email, website_domain)
        if is_valid:
            valid_emails.append(email)

    return valid_emails


def extract_rating_from_name(name: str) -> Tuple[str, Optional[float], Optional[int]]:
    """
    Extract rating and review count from business name if embedded.

    Args:
        name: Business name potentially containing rating info

    Returns:
        Tuple of (cleaned_name, rating, review_count)
    """
    if not name:
        return "", None, None

    rating = None
    review_count = None
    cleaned = name

    # Look for patterns like "4.8 (500+ reviews)" or "4.8 stars"
    rating_pattern = r'(\d+\.?\d?)\s*(?:stars?|\u2B50|\u2605)?\s*(?:\((\d+\.?\d*[Kk]?\+?)\s*reviews?\))?'
    match = re.search(rating_pattern, cleaned)
    if match:
        try:
            rating = float(match.group(1))
            if match.group(2):
                count_str = match.group(2).replace('+', '').lower()
                if 'k' in count_str:
                    review_count = int(float(count_str.replace('k', '')) * 1000)
                else:
                    review_count = int(float(count_str))
        except (ValueError, TypeError):
            pass

    # Clean the name
    cleaned = clean_business_name(cleaned)

    return cleaned, rating, review_count
