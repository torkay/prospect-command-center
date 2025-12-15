"""Configuration settings for the Prospect Command Center."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Unified settings with YAML override support."""

    # API Keys (from environment)
    serpapi_key: str = field(default_factory=lambda: os.environ.get("SERPAPI_KEY", ""))

    # Priority calculation weights (must sum to 1.0)
    fit_weight: float = 0.4
    opportunity_weight: float = 0.6

    # Fit score component weights (max 100 total)
    fit_website: int = 15
    fit_phone: int = 15
    fit_email: int = 10
    fit_maps: int = 15
    fit_rating: int = 10
    fit_reviews: int = 10
    fit_ads: int = 10
    fit_organic: int = 15

    # Opportunity score component weights
    opp_no_analytics: int = 15
    opp_no_pixel: int = 10
    opp_no_booking: int = 15
    opp_no_email: int = 10
    opp_diy_cms: int = 10
    opp_slow_site: int = 10
    opp_has_ads: int = -10  # Negative = reduces opportunity
    opp_poor_seo: int = 20

    # Performance settings
    enrichment_timeout: int = 10
    enrichment_parallel: int = 1
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour

    # DIY CMS list (high opportunity)
    diy_cms: list = field(default_factory=lambda: [
        "Wix", "Weebly", "GoDaddy Website Builder",
        "Squarespace", "Jimdo", "Carrd"
    ])

    # Extra domains to filter (in addition to DIRECTORY_DOMAINS)
    extra_filter_domains: list = field(default_factory=list)


def load_config(path: Optional[str] = None) -> Settings:
    """
    Load settings from YAML file with environment overrides.

    Priority: environment > config file > defaults

    Args:
        path: Path to YAML config file (optional)

    Returns:
        Settings instance with merged configuration
    """
    settings = Settings()

    if path:
        config_path = Path(path)
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            # Apply config values
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

    # Environment overrides (always win)
    if os.environ.get("SERPAPI_KEY"):
        settings.serpapi_key = os.environ["SERPAPI_KEY"]

    return settings


@dataclass
class ScraperConfig:
    """Configuration for the scraper behavior."""

    # Browser settings
    headless: bool = True
    browser_timeout: int = 30000  # ms

    # Search settings
    search_delay_min: float = 2.0
    search_delay_max: float = 5.0
    max_retries: int = 3

    # Enrichment settings
    enrichment_timeout: int = 10000  # ms
    max_concurrent_requests: int = 5

    # Output settings
    default_output: str = "prospects.csv"
    default_format: str = "csv"

    # Debug settings
    debug: bool = False
    debug_dir: str = "debug_output"


@dataclass
class ScoringConfig:
    """Configuration for scoring weights."""

    # Fit score weights
    website_weight: int = 15
    phone_weight: int = 15
    email_weight: int = 10
    maps_presence_weight: int = 15
    good_rating_weight: int = 10
    review_count_weight: int = 10
    ads_presence_weight: int = 10
    organic_top10_weight: int = 15

    # Opportunity score weights
    no_analytics_weight: int = 15
    no_pixel_weight: int = 10
    no_booking_weight: int = 15
    no_contact_weight: int = 10
    weak_cms_weight: int = 10
    slow_site_weight: int = 10
    running_ads_penalty: int = -10
    good_tracking_penalty: int = -10
    poor_maps_ranking_weight: int = 10
    poor_organic_ranking_weight: int = 20


# Directory domains to filter out
DIRECTORY_DOMAINS = {
    # Social media
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
    "reddit.com",
    "quora.com",
    "pinterest.com",
    "threads.net",

    # Australian directories
    "yelp.com",
    "yelp.com.au",
    "yellowpages.com.au",
    "yellowpages.com",
    "truelocal.com.au",
    "hotfrog.com.au",
    "oneflare.com.au",
    "hipages.com.au",
    "productreview.com.au",
    "localsearch.com.au",
    "startlocal.com.au",
    "whereis.com",
    "whitepages.com.au",
    "aussieweb.com.au",
    "fyple.com.au",
    "brownbook.net",
    "wordofmouth.com.au",
    "findabusiness.com.au",
    "cylex.com.au",
    "opendi.com.au",
    "tuugo.com.au",
    "yalwa.com.au",

    # Marketplaces - look like real businesses but are aggregators
    "airtasker.com",
    "airtasker.com.au",
    "serviceseeking.com.au",
    "bark.com",
    "bark.com.au",
    "thumbtack.com",
    "homeadvisor.com",
    "angi.com",
    "angieslist.com",
    "taskrabbit.com",
    "fiverr.com",
    "upwork.com",
    "freelancer.com",
    "freelancer.com.au",

    # Job boards
    "seek.com.au",
    "indeed.com",
    "indeed.com.au",
    "au.indeed.com",
    "glassdoor.com",
    "glassdoor.com.au",
    "jora.com",
    "careerone.com.au",

    # Review aggregators
    "birdeye.com",
    "trustpilot.com",
    "reviews.io",
    "podium.com",

    # Generic/tech
    "wikipedia.org",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "apple.com",
    "g2.com",
    "capterra.com",
    "crunchbase.com",
    "medium.com",
    "github.com",
    "stackoverflow.com",

    # News/media (not businesses)
    "news.com.au",
    "smh.com.au",
    "theaustralian.com.au",
    "abc.net.au",
    "9news.com.au",
    "7news.com.au",
    "sbs.com.au",
}

# URL patterns that indicate directory/social content (even on legitimate domains)
DIRECTORY_URL_PATTERNS = [
    "/r/",              # Reddit subreddits
    "/company/",        # LinkedIn company pages
    "/biz/",            # Yelp business pages
    "/local/",          # Various directory patterns
    "/business/",       # Facebook business pages
    "/pages/",          # Facebook pages
    "/profile/",        # Social profiles
    "/user/",           # User profiles
    "/comments/",       # Reddit comments
    "/questions/",      # Q&A sites
    "/listing/",        # Directory listings
    "/directory/",      # Directory pages
    "/find-a-",         # Find-a-tradesman style
    "/search?",         # Search results pages
    "/review/",         # Review pages
    "/reviews/",        # Review pages
    "/category/",       # Category listings
    "/service-provider/",  # Service provider directories
    "/tradies/",        # Tradie directories
]

# CMS signatures for detection
CMS_SIGNATURES = {
    "WordPress": ["/wp-content/", "/wp-includes/", "wp-json", "wordpress"],
    "Wix": ["wix.com", "wixsite.com", "_wix_browser_sess", "wix-code"],
    "Squarespace": ["squarespace.com", "static.squarespace", "sqsp.net"],
    "Shopify": ["cdn.shopify.com", "myshopify.com", "shopify"],
    "Webflow": ["webflow.com", "assets-global.website-files", "webflow.io"],
    "Weebly": ["weebly.com", "weeblycloud.com"],
    "GoDaddy Website Builder": ["godaddy.com", "secureserver.net", "godaddysites"],
    "Joomla": ["joomla", "/components/com_"],
    "Drupal": ["drupal", "/sites/default/"],
}

# Tracking signatures for detection
TRACKING_SIGNATURES = {
    "google_analytics": [
        "google-analytics.com",
        "gtag(",
        "ga(",
        "G-",
        "UA-",
        "googletagmanager.com",
    ],
    "facebook_pixel": [
        "facebook.com/tr",
        "fbq(",
        "connect.facebook.net",
    ],
    "google_ads": [
        "googleadservices.com",
        "googlesyndication.com",
        "AW-",
        "google_conversion",
    ],
}

# Booking system signatures
BOOKING_SIGNATURES = [
    "calendly.com",
    "acuityscheduling",
    "youcanbook.me",
    "setmore.com",
    "square.site/book",
    "fresha.com",
    "book-online",
    "book-now",
    "schedule-appointment",
    "hubspot.com/meetings",
    "bookings.google.com",
    "appointlet.com",
    "simplybook.me",
    "timify.com",
]

# Australian phone patterns
PHONE_PATTERNS = [
    r'(?:\+61|0)[2-478](?:[ -]?\d){8}',  # Standard landline/mobile
    r'\(\d{2}\)[ -]?\d{4}[ -]?\d{4}',     # (02) 1234 5678 format
    r'1[38]00[ -]?\d{3}[ -]?\d{3}',       # 1300/1800 numbers
    r'13[ -]?\d{2}[ -]?\d{2}',            # 13 XX XX short numbers
]

# Email pattern
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Spam email patterns to filter out
SPAM_EMAIL_PATTERNS = [
    r'.*@error-tracking\..*',
    r'.*@sentry\.io',
    r'.*@bugsnag\.com',
    r'.*@errortracking\..*',
    r'.*@tracking\..*',
    r'.*noreply@.*',
    r'.*no-reply@.*',
    r'.*donotreply@.*',
    r'.*do-not-reply@.*',
    r'.*mailer-daemon@.*',
    r'.*postmaster@.*',
    r'.*automated@.*',
    r'.*notifications@.*',
    r'[a-f0-9]{20,}@.*',  # Hash-based emails like error tracking IDs
]

# Spam email domains to filter out
SPAM_EMAIL_DOMAINS = {
    'error-tracking.reddit.com',
    'sentry.io',
    'bugsnag.com',
    'wix.com',
    'wixpress.com',
    'wordpress.com',
    'squarespace.com',
    'squarespace-mail.com',
    'mailchimp.com',
    'sendgrid.net',
    'amazonses.com',
    'mailgun.org',
    'mandrillapp.com',
    'sparkpostmail.com',
    'postmarkapp.com',
    'intercom-mail.com',
    'zendesk.com',
    'freshdesk.com',
}
