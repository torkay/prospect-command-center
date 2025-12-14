"""Data models for the prospect scraper."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class AdResult:
    """Represents a Google Ads result from SERP."""

    position: int
    headline: str
    display_url: str
    destination_url: str
    description: str
    is_top: bool  # True if ad is above organic results


@dataclass
class MapsResult:
    """Represents a Google Maps/Local Pack result from SERP."""

    position: int
    name: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    category: Optional[str] = None
    address: str = ""
    phone: Optional[str] = None
    website: Optional[str] = None


@dataclass
class OrganicResult:
    """Represents an organic search result from SERP."""

    position: int
    title: str
    url: str
    domain: str
    snippet: str


@dataclass
class SerpResults:
    """Container for all SERP results from a single search."""

    query: str
    location: str
    timestamp: datetime = field(default_factory=datetime.now)
    ads: list[AdResult] = field(default_factory=list)
    maps: list[MapsResult] = field(default_factory=list)
    organic: list[OrganicResult] = field(default_factory=list)


@dataclass
class WebsiteSignals:
    """Marketing signals extracted from a website."""

    url: str
    reachable: bool = False
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    cms: Optional[str] = None
    has_google_analytics: bool = False
    has_facebook_pixel: bool = False
    has_google_ads: bool = False
    has_booking_system: bool = False
    load_time_ms: Optional[int] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    social_links: list[str] = field(default_factory=list)


@dataclass
class Prospect:
    """A potential prospect/lead with all gathered data."""

    name: str
    website: Optional[str] = None
    domain: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    # SERP presence
    found_in_ads: bool = False
    ad_position: Optional[int] = None
    found_in_maps: bool = False
    maps_position: Optional[int] = None
    found_in_organic: bool = False
    organic_position: Optional[int] = None

    # Google Business Profile data
    rating: Optional[float] = None
    review_count: Optional[int] = None
    category: Optional[str] = None

    # Contact info
    emails: list[str] = field(default_factory=list)

    # Website signals
    signals: Optional[WebsiteSignals] = None

    # Scores
    fit_score: int = 0
    opportunity_score: int = 0
    priority_score: float = 0.0
    opportunity_notes: str = ""

    # Metadata
    source: str = ""  # Where this prospect was first found
    scraped_at: datetime = field(default_factory=datetime.now)

    def merge_from(self, other: "Prospect") -> None:
        """Merge data from another prospect record (for deduplication)."""
        # Keep existing values, fill in missing ones
        if not self.website and other.website:
            self.website = other.website
            self.domain = other.domain
        if not self.phone and other.phone:
            self.phone = other.phone
        if not self.address and other.address:
            self.address = other.address
        if not self.rating and other.rating:
            self.rating = other.rating
        if not self.review_count and other.review_count:
            self.review_count = other.review_count
        if not self.category and other.category:
            self.category = other.category

        # Merge SERP presence
        if other.found_in_ads:
            self.found_in_ads = True
            if not self.ad_position or other.ad_position < self.ad_position:
                self.ad_position = other.ad_position
        if other.found_in_maps:
            self.found_in_maps = True
            if not self.maps_position or other.maps_position < self.maps_position:
                self.maps_position = other.maps_position
        if other.found_in_organic:
            self.found_in_organic = True
            if not self.organic_position or other.organic_position < self.organic_position:
                self.organic_position = other.organic_position

        # Merge emails (unique)
        for email in other.emails:
            if email not in self.emails:
                self.emails.append(email)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = {
            "name": self.name,
            "website": self.website,
            "domain": self.domain,
            "phone": self.phone,
            "address": self.address,
            "emails": self.emails or [],
            "rating": self.rating,
            "review_count": self.review_count,
            "category": self.category,
            "found_in_ads": self.found_in_ads,
            "ad_position": self.ad_position,
            "found_in_maps": self.found_in_maps,
            "maps_position": self.maps_position,
            "found_in_organic": self.found_in_organic,
            "organic_position": self.organic_position,
            "fit_score": self.fit_score,
            "opportunity_score": self.opportunity_score,
            "priority_score": round(self.priority_score, 2),
            "opportunity_notes": self.opportunity_notes,
            "source": self.source,
        }

        # Add signals if available
        if self.signals:
            data["signals"] = {
                "reachable": self.signals.reachable,
                "cms": self.signals.cms,
                "has_google_analytics": self.signals.has_google_analytics,
                "has_facebook_pixel": self.signals.has_facebook_pixel,
                "has_google_ads": self.signals.has_google_ads,
                "has_booking_system": self.signals.has_booking_system,
                "load_time_ms": self.signals.load_time_ms,
            }

        return data


@dataclass
class CrawlResult:
    """Result from crawling a website."""

    url: str
    success: bool
    html: str = ""
    load_time_ms: int = 0
    status_code: Optional[int] = None
    error: Optional[str] = None
    final_url: Optional[str] = None  # After redirects
