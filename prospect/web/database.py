"""Database models for prospect persistence."""

import os
import logging
from datetime import datetime
from typing import Optional, List, Generator
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """
    Get database URL based on environment.

    Railway: Uses /data volume for persistence (if mounted)
    Fallback: Uses /app/data for Railway without volume
    Local: Uses ./prospects.db in project root
    """
    # Check for explicit DATABASE_URL first (allows override)
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    # Check for Railway environment
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        # Try /data first (persistent volume mount point)
        if os.path.exists("/data") and os.access("/data", os.W_OK):
            return "sqlite:////data/prospects.db"

        # Fallback to /app/data (within the app directory)
        # This won't persist across deploys but allows the app to start
        os.makedirs("/app/data", exist_ok=True)
        return "sqlite:////app/data/prospects.db"

    # Local development
    return "sqlite:///./prospects.db"


DATABASE_URL = get_database_url()

# Handle SQLite-specific settings
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User account for multi-tenant access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)

    # Subscription
    tier = Column(String(50), default="scout")  # scout, hunter, command
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="none")  # none, active, past_due, canceled

    # Usage limits (set based on tier)
    searches_limit = Column(Integer, default=100)
    enrichments_limit = Column(Integer, default=50)

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Email preferences
    email_notifications = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Onboarding
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)  # 0=not started, 1=welcome, 2=first_search, 3=understand_scores, 4=complete
    first_login_at = Column(DateTime, nullable=True)

    # Relationships
    searches = relationship("Search", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")
    usage_records = relationship("UsageRecord", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class UsageRecord(Base):
    """Monthly usage tracking per user."""
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Period (monthly)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Usage counts
    searches_used = Column(Integer, default=0)
    enrichments_used = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="usage_records")

    def __repr__(self):
        return f"<UsageRecord user={self.user_id} period={self.period_start}>"


class SearchConfig(Base):
    """
    Search depth configuration.

    Defines tiered search depths for controlling API usage and prospect coverage.
    """
    __tablename__ = "search_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # quick, standard, deep, exhaustive
    description = Column(String(255))

    # Pagination
    organic_pages = Column(Integer, default=1)  # How many pages of organic results
    maps_pages = Column(Integer, default=1)     # How many pages of maps results

    # Query expansion
    use_query_variations = Column(Boolean, default=False)
    query_variations = Column(JSON, default=[])  # Additional query templates

    # Location expansion
    use_location_expansion = Column(Boolean, default=False)
    expansion_radius_km = Column(Integer, default=0)  # 0 = no expansion
    max_locations = Column(Integer, default=1)

    # Search types
    search_organic = Column(Boolean, default=True)
    search_maps = Column(Boolean, default=True)
    search_local_services = Column(Boolean, default=False)

    # Cost controls
    max_api_calls = Column(Integer, default=5)
    estimated_cost_cents = Column(Integer, default=5)


class Campaign(Base):
    """Saved search campaign - reusable search configuration."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    business_type = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    limit = Column(Integer, default=20)
    filters = Column(JSON, default={})

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_run_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)

    # Color/icon for UI
    color = Column(String(20), default="blue")
    icon = Column(String(50), default="search")

    # Relationships
    user = relationship("User", back_populates="campaigns")
    searches = relationship("Search", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign {self.name}: {self.business_type} in {self.location}>"


class Search(Base):
    """Individual search run - snapshot of results at a point in time."""
    __tablename__ = "searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)

    # Search parameters
    business_type = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    query = Column(String(500))

    # Results summary
    total_found = Column(Integer, default=0)
    avg_fit_score = Column(Float, default=0)
    avg_opportunity_score = Column(Float, default=0)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, running, complete, error
    error = Column(Text, nullable=True)

    # Search depth tracking
    config_name = Column(String(50), default="standard")  # quick, standard, deep, exhaustive
    api_calls_made = Column(Integer, default=0)
    api_calls_budget = Column(Integer, default=5)
    actual_cost_cents = Column(Integer, default=0)

    # Expansion tracking
    queries_searched = Column(JSON, default=[])  # All query variations used
    locations_searched = Column(JSON, default=[])  # All locations searched
    pages_fetched = Column(JSON, default={})  # {"organic": [1,2,3], "maps": [1]}

    # Results by source
    results_from_organic = Column(Integer, default=0)
    results_from_maps = Column(Integer, default=0)
    results_from_ads = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="searches")
    campaign = relationship("Campaign", back_populates="searches")
    prospects = relationship("Prospect", back_populates="search", cascade="all, delete-orphan")


class Prospect(Base):
    """Individual prospect - persisted across searches for tracking."""
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("searches.id"))

    # Identity (used for deduplication across searches)
    domain = Column(String(255), index=True)
    name = Column(String(255))

    # Contact
    website = Column(String(500))
    phone = Column(String(50))
    emails = Column(Text)  # JSON array or comma-separated
    address = Column(String(500))

    # Google data
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)

    # SERP presence
    found_in_ads = Column(Boolean, default=False)
    found_in_maps = Column(Boolean, default=False)
    found_in_organic = Column(Boolean, default=False)
    organic_position = Column(Integer, nullable=True)
    maps_position = Column(Integer, nullable=True)

    # Enrichment
    cms = Column(String(50))
    has_analytics = Column(Boolean, default=False)
    has_facebook_pixel = Column(Boolean, default=False)
    has_booking = Column(Boolean, default=False)
    load_time_ms = Column(Integer, nullable=True)

    # Scores
    fit_score = Column(Integer, default=0)
    opportunity_score = Column(Integer, default=0)
    priority_score = Column(Float, default=0)
    opportunity_notes = Column(Text)

    # User workflow
    status = Column(String(20), default="new")  # new, qualified, contacted, meeting, won, lost, skipped
    user_notes = Column(Text)
    contacted_at = Column(DateTime, nullable=True)
    follow_up_at = Column(DateTime, nullable=True)

    # Metadata
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    seen_count = Column(Integer, default=1)

    # Tags (JSON array)
    tags = Column(JSON, default=[])

    # Relationships
    search = relationship("Search", back_populates="prospects")

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "search_id": self.search_id,
            "domain": self.domain,
            "name": self.name,
            "website": self.website,
            "phone": self.phone,
            "emails": self.emails,
            "address": self.address,
            "rating": self.rating,
            "review_count": self.review_count,
            "found_in_ads": self.found_in_ads,
            "found_in_maps": self.found_in_maps,
            "found_in_organic": self.found_in_organic,
            "organic_position": self.organic_position,
            "maps_position": self.maps_position,
            "cms": self.cms,
            "has_analytics": self.has_analytics,
            "has_facebook_pixel": self.has_facebook_pixel,
            "has_booking": self.has_booking,
            "load_time_ms": self.load_time_ms,
            "fit_score": self.fit_score,
            "opportunity_score": self.opportunity_score,
            "priority_score": self.priority_score,
            "opportunity_notes": self.opportunity_notes,
            "status": self.status,
            "user_notes": self.user_notes,
            "contacted_at": self.contacted_at.isoformat() if self.contacted_at else None,
            "follow_up_at": self.follow_up_at.isoformat() if self.follow_up_at else None,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "seen_count": self.seen_count,
            "tags": self.tags or [],
        }


class Tag(Base):
    """User-defined tags for organizing prospects."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(20), default="gray")
    created_at = Column(DateTime, default=datetime.utcnow)


class ExportHistory(Base):
    """Track exports for audit trail."""
    __tablename__ = "export_history"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("searches.id"), nullable=True)

    export_type = Column(String(20))  # csv, json, sheets
    record_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # For Sheets exports
    sheet_url = Column(String(500), nullable=True)


class MarketingEvent(Base):
    """Marketing events tracked for anonymous activity analysis."""
    __tablename__ = "marketing_events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)
    campaign = Column(String(255), nullable=True)
    anonymous_id = Column(String(255), nullable=True)
    client_id = Column(String(255), nullable=True)
    page_url = Column(String(500), nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # 'metadata' is reserved in SQLAlchemy Declarative models.
    event_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("MarketingLead", back_populates="event")


class MarketingLead(Base):
    """Leads captured from marketing forms or events."""
    __tablename__ = "marketing_leads"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("marketing_events.id"), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    source = Column(String(255), nullable=True)
    campaign = Column(String(255), nullable=True)
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    # 'metadata' is reserved in SQLAlchemy Declarative models.
    lead_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("MarketingEvent", back_populates="leads")


def seed_search_configs(db: Session) -> None:
    """Seed default search configurations."""
    configs = [
        {
            "name": "quick",
            "description": "Fast scan - first page only",
            "organic_pages": 1,
            "maps_pages": 0,
            "use_query_variations": False,
            "use_location_expansion": False,
            "search_organic": True,
            "search_maps": True,
            "search_local_services": False,
            "max_api_calls": 1,
            "estimated_cost_cents": 1,
        },
        {
            "name": "standard",
            "description": "Balanced search - good coverage",
            "organic_pages": 2,
            "maps_pages": 1,
            "use_query_variations": True,
            "query_variations": ["{business_type} services", "{business_type} near me"],
            "use_location_expansion": False,
            "search_organic": True,
            "search_maps": True,
            "search_local_services": False,
            "max_api_calls": 5,
            "estimated_cost_cents": 5,
        },
        {
            "name": "deep",
            "description": "Comprehensive - multiple queries and locations",
            "organic_pages": 3,
            "maps_pages": 2,
            "use_query_variations": True,
            "query_variations": [
                "{business_type} services",
                "{business_type} near me",
                "best {business_type}",
                "local {business_type}",
            ],
            "use_location_expansion": True,
            "expansion_radius_km": 10,
            "max_locations": 5,
            "search_organic": True,
            "search_maps": True,
            "search_local_services": True,
            "max_api_calls": 20,
            "estimated_cost_cents": 15,
        },
        {
            "name": "exhaustive",
            "description": "Full market mapping - maximum coverage",
            "organic_pages": 5,
            "maps_pages": 3,
            "use_query_variations": True,
            "query_variations": [
                "{business_type} services",
                "{business_type} near me",
                "best {business_type}",
                "local {business_type}",
                "emergency {business_type}",
                "cheap {business_type}",
                "24 hour {business_type}",
                "{business_type} company",
            ],
            "use_location_expansion": True,
            "expansion_radius_km": 25,
            "max_locations": 10,
            "search_organic": True,
            "search_maps": True,
            "search_local_services": True,
            "max_api_calls": 50,
            "estimated_cost_cents": 40,
        },
    ]

    try:
        for config in configs:
            existing = db.query(SearchConfig).filter(SearchConfig.name == config["name"]).first()
            if not existing:
                db.add(SearchConfig(**config))
                logger.debug(f"Added search config: {config['name']}")

        db.commit()
        logger.info("Search configs seeded successfully")
    except Exception as e:
        logger.error(f"Error in seed_search_configs: {e}")
        db.rollback()
        raise


def init_db():
    """Initialize database tables and seed data."""
    try:
        logger.info(f"Initializing database at: {DATABASE_URL}")

        # Create tables (non-blocking for SQLite)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Seed search configs in a separate session
        db = SessionLocal()
        try:
            seed_search_configs(db)
            logger.info("Search configs seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding search configs: {e}")
            db.rollback()
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        # Don't fail the app startup, just log the error
        pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_prospects_from_results(db: Session, search_id: int, results: list) -> List[Prospect]:
    """
    Save prospect results to database.

    Converts search results (Prospect model from models.py) to database Prospect records.
    Uses bulk_insert_mappings for efficient batch insertion.
    """
    prospect_dicts = []
    for r in results:
        emails = ",".join(r.emails) if r.emails else None
        prospect_dicts.append({
            "search_id": search_id,
            "domain": r.domain,
            "name": r.name,
            "website": r.website,
            "phone": r.phone,
            "emails": emails,
            "address": r.address,
            "rating": r.rating,
            "review_count": r.review_count,
            "found_in_ads": r.found_in_ads,
            "found_in_maps": r.found_in_maps,
            "found_in_organic": r.found_in_organic,
            "organic_position": r.organic_position,
            "maps_position": r.maps_position,
            "cms": r.signals.cms if r.signals else None,
            "has_analytics": r.signals.has_google_analytics if r.signals else False,
            "has_facebook_pixel": r.signals.has_facebook_pixel if r.signals else False,
            "has_booking": r.signals.has_booking_system if r.signals else False,
            "load_time_ms": r.signals.load_time_ms if r.signals else None,
            "fit_score": r.fit_score,
            "opportunity_score": r.opportunity_score,
            "priority_score": r.priority_score,
            "opportunity_notes": r.opportunity_notes,
        })

    db.bulk_insert_mappings(Prospect, prospect_dicts)
    db.commit()

    return db.query(Prospect).filter(Prospect.search_id == search_id).all()
