"""Contact information extraction (emails, phones)."""

import re
from typing import List

from ..config import PHONE_PATTERNS, EMAIL_PATTERN, SPAM_EMAIL_PATTERNS, SPAM_EMAIL_DOMAINS


def is_spam_email(email: str) -> bool:
    """
    Check if email is likely spam/system email.

    Args:
        email: Email address to check

    Returns:
        True if email appears to be spam/system/tracking email
    """
    email_lower = email.lower()

    # Check domain blocklist
    if "@" in email_lower:
        domain = email_lower.split("@")[-1]
        if domain in SPAM_EMAIL_DOMAINS:
            return True

    # Check patterns
    for pattern in SPAM_EMAIL_PATTERNS:
        if re.match(pattern, email_lower):
            return True

    return False


def extract_emails(html: str) -> List[str]:
    """
    Extract valid contact email addresses from HTML content.

    Args:
        html: Raw HTML content

    Returns:
        List of unique, valid email addresses found
    """
    if not html:
        return []

    # Find all email patterns
    emails = re.findall(EMAIL_PATTERN, html, re.IGNORECASE)

    # Filter and clean
    valid_emails = []
    seen = set()

    # Common false positives to filter (in addition to spam patterns)
    exclude_patterns = [
        r"@example\.",
        r"@test\.",
        r"@localhost",
        r"@domain\.",
        r"@email\.",
        r"@your",
        r"@site",
        r"@sample\.",
        r"@placeholder\.",
        r"cloudflare",
        r"googleapis",
        r"jquery",
        r"bootstrap",
        r"fontawesome",
        r"\.png$",
        r"\.jpg$",
        r"\.gif$",
        r"\.css$",
        r"\.js$",
        r"\.svg$",
        r"\.woff",
        r"\.webp$",
        r"@2x\.",  # Retina image naming convention
        r"@3x\.",  # Retina image naming convention
    ]

    for email in emails:
        email_lower = email.lower()

        # Skip if already seen
        if email_lower in seen:
            continue

        # Skip spam/system emails
        if is_spam_email(email_lower):
            continue

        # Skip if matches exclude patterns
        if any(re.search(pattern, email_lower) for pattern in exclude_patterns):
            continue

        # Skip very long emails (probably not real)
        if len(email) > 100:
            continue

        # Skip emails that look like hashes/IDs (many hex chars before @)
        local_part = email_lower.split("@")[0]
        hex_chars = sum(1 for c in local_part if c in "0123456789abcdef")
        if len(local_part) > 15 and hex_chars / len(local_part) > 0.7:
            continue

        seen.add(email_lower)
        valid_emails.append(email_lower)

    # Limit to reasonable number
    return valid_emails[:5]


def extract_phones(html: str) -> List[str]:
    """
    Extract Australian phone numbers from HTML content.

    Args:
        html: Raw HTML content

    Returns:
        List of unique phone numbers found
    """
    if not html:
        return []

    phones = []
    seen = set()

    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, html)
        for match in matches:
            # Normalize the phone number
            normalized = normalize_phone(match)
            if normalized and normalized not in seen:
                seen.add(normalized)
                phones.append(normalized)

    return phones


def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number to a consistent format.

    Args:
        phone: Raw phone number string

    Returns:
        Normalized phone number (digits only with spaces)
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    digits = re.sub(r"[^\d+]", "", phone)

    # Skip if too short
    if len(digits) < 8:
        return ""

    # Format based on type
    if digits.startswith("+61"):
        # International format: +61 4XX XXX XXX
        digits = digits[3:]  # Remove +61
        if digits.startswith("0"):
            digits = digits[1:]
        return format_au_number(digits)
    elif digits.startswith("0"):
        # Local format: 04XX XXX XXX or 0X XXXX XXXX
        return format_au_number(digits[1:])
    elif digits.startswith("1300") or digits.startswith("1800"):
        # 1300/1800 numbers
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    elif digits.startswith("13") and len(digits) == 6:
        # 13 XX XX short numbers
        return f"{digits[:2]} {digits[2:4]} {digits[4:]}"

    return phone.strip()


def format_au_number(digits: str) -> str:
    """
    Format Australian number digits.

    Args:
        digits: Phone digits without country code or leading zero

    Returns:
        Formatted phone number
    """
    if len(digits) == 9:
        # Mobile: 4XX XXX XXX
        if digits.startswith("4"):
            return f"0{digits[0:3]} {digits[3:6]} {digits[6:]}"
        # Landline: X XXXX XXXX
        else:
            return f"0{digits[0]} {digits[1:5]} {digits[5:]}"

    return digits


def extract_contact_page_url(html: str, base_url: str) -> str:
    """
    Find the contact page URL in HTML.

    Args:
        html: Raw HTML content
        base_url: Base URL for resolving relative links

    Returns:
        Contact page URL if found, empty string otherwise
    """
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    contact_patterns = [
        r"/contact",
        r"/contact-us",
        r"/get-in-touch",
        r"/reach-us",
        r"/enquiry",
        r"/inquiry",
    ]

    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        text = link.get_text(strip=True).lower()

        # Check href patterns
        for pattern in contact_patterns:
            if pattern in href:
                return urljoin(base_url, link["href"])

        # Check link text
        if "contact" in text or "get in touch" in text:
            return urljoin(base_url, link["href"])

    return ""
