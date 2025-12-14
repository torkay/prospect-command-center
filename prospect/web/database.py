"""Database models for prospect persistence."""

import os
from datetime import datetime
from typing import Optional, List, Generator
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base


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


class Campaign(Base):
    """Saved search campaign - reusable search configuration."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
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
    searches = relationship("Search", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign {self.name}: {self.business_type} in {self.location}>"


class Search(Base):
    """Individual search run - snapshot of results at a point in time."""
    __tablename__ = "searches"

    id = Column(Integer, primary_key=True, index=True)
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

    # Relationships
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


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


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
    """
    prospects = []
    for r in results:
        # Extract emails as comma-separated string
        emails = ",".join(r.emails) if r.emails else None

        prospect = Prospect(
            search_id=search_id,
            domain=r.domain,
            name=r.name,
            website=r.website,
            phone=r.phone,
            emails=emails,
            address=r.address,
            rating=r.rating,
            review_count=r.review_count,
            found_in_ads=r.found_in_ads,
            found_in_maps=r.found_in_maps,
            found_in_organic=r.found_in_organic,
            organic_position=r.organic_position,
            maps_position=r.maps_position,
            cms=r.signals.cms if r.signals else None,
            has_analytics=r.signals.has_google_analytics if r.signals else False,
            has_facebook_pixel=r.signals.has_facebook_pixel if r.signals else False,
            has_booking=r.signals.has_booking_system if r.signals else False,
            load_time_ms=r.signals.load_time_ms if r.signals else None,
            fit_score=r.fit_score,
            opportunity_score=r.opportunity_score,
            priority_score=r.priority_score,
            opportunity_notes=r.opportunity_notes,
        )
        db.add(prospect)
        prospects.append(prospect)

    db.commit()
    return prospects
