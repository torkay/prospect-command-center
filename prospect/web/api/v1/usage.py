"""Usage tracking and limits API."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from prospect.web.database import get_db, User, UsageRecord
from prospect.web.auth import get_current_user

router = APIRouter(prefix="/usage", tags=["usage"])


class UsageResponse(BaseModel):
    """Current usage stats for the user."""
    # Current period
    period_start: datetime
    period_end: datetime

    # Searches
    searches_used: int
    searches_limit: int
    searches_remaining: int
    searches_percent: float

    # Enrichments
    enrichments_used: int
    enrichments_limit: int
    enrichments_remaining: int
    enrichments_percent: float

    # Tier info
    tier: str
    subscription_status: str


class UsageAlert(BaseModel):
    """Usage alert for approaching limits."""
    type: str  # "warning", "limit_reached"
    resource: str  # "searches", "enrichments"
    message: str
    percent_used: float


def get_current_period() -> tuple[datetime, datetime]:
    """Get the current billing period (monthly, starting on the 1st)."""
    now = datetime.utcnow()
    period_start = datetime(now.year, now.month, 1)

    # Calculate end of month
    if now.month == 12:
        period_end = datetime(now.year + 1, 1, 1)
    else:
        period_end = datetime(now.year, now.month + 1, 1)

    return period_start, period_end


def get_or_create_usage_record(db: Session, user: User) -> UsageRecord:
    """Get or create the usage record for the current period."""
    period_start, period_end = get_current_period()

    # Find existing record for this period
    record = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start == period_start,
    ).first()

    if record is None:
        # Create new record for this period
        record = UsageRecord(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
            searches_used=0,
            enrichments_used=0,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


def check_search_limit(db: Session, user: User) -> bool:
    """Check if user can perform a search. Returns True if allowed."""
    record = get_or_create_usage_record(db, user)
    return record.searches_used < user.searches_limit


def check_enrichment_limit(db: Session, user: User, count: int = 1) -> bool:
    """Check if user can perform enrichments. Returns True if allowed."""
    record = get_or_create_usage_record(db, user)
    return (record.enrichments_used + count) <= user.enrichments_limit


def increment_search_usage(db: Session, user: User) -> UsageRecord:
    """Increment the search usage counter."""
    record = get_or_create_usage_record(db, user)
    record.searches_used += 1
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def increment_enrichment_usage(db: Session, user: User, count: int = 1) -> UsageRecord:
    """Increment the enrichment usage counter."""
    record = get_or_create_usage_record(db, user)
    record.enrichments_used += count
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=UsageResponse)
def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current usage statistics for the authenticated user.
    """
    record = get_or_create_usage_record(db, current_user)

    searches_remaining = max(0, current_user.searches_limit - record.searches_used)
    enrichments_remaining = max(0, current_user.enrichments_limit - record.enrichments_used)

    searches_percent = (record.searches_used / current_user.searches_limit * 100) if current_user.searches_limit > 0 else 0
    enrichments_percent = (record.enrichments_used / current_user.enrichments_limit * 100) if current_user.enrichments_limit > 0 else 0

    return UsageResponse(
        period_start=record.period_start,
        period_end=record.period_end,
        searches_used=record.searches_used,
        searches_limit=current_user.searches_limit,
        searches_remaining=searches_remaining,
        searches_percent=round(searches_percent, 1),
        enrichments_used=record.enrichments_used,
        enrichments_limit=current_user.enrichments_limit,
        enrichments_remaining=enrichments_remaining,
        enrichments_percent=round(enrichments_percent, 1),
        tier=current_user.tier,
        subscription_status=current_user.subscription_status,
    )


@router.get("/alerts", response_model=list[UsageAlert])
def get_usage_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get usage alerts for the authenticated user.

    Returns warnings when approaching limits (80%) and alerts when limits are reached.
    """
    record = get_or_create_usage_record(db, current_user)
    alerts = []

    # Check searches
    if current_user.searches_limit > 0:
        searches_percent = record.searches_used / current_user.searches_limit * 100
        if searches_percent >= 100:
            alerts.append(UsageAlert(
                type="limit_reached",
                resource="searches",
                message=f"You've used all {current_user.searches_limit} searches this month. Upgrade your plan for more.",
                percent_used=100,
            ))
        elif searches_percent >= 80:
            remaining = current_user.searches_limit - record.searches_used
            alerts.append(UsageAlert(
                type="warning",
                resource="searches",
                message=f"You have {remaining} searches remaining this month.",
                percent_used=round(searches_percent, 1),
            ))

    # Check enrichments
    if current_user.enrichments_limit > 0:
        enrichments_percent = record.enrichments_used / current_user.enrichments_limit * 100
        if enrichments_percent >= 100:
            alerts.append(UsageAlert(
                type="limit_reached",
                resource="enrichments",
                message=f"You've used all {current_user.enrichments_limit} enrichments this month. Upgrade your plan for more.",
                percent_used=100,
            ))
        elif enrichments_percent >= 80:
            remaining = current_user.enrichments_limit - record.enrichments_used
            alerts.append(UsageAlert(
                type="warning",
                resource="enrichments",
                message=f"You have {remaining} enrichments remaining this month.",
                percent_used=round(enrichments_percent, 1),
            ))

    return alerts


# Tier limits configuration
TIER_LIMITS = {
    "scout": {"searches": 100, "enrichments": 50},
    "hunter": {"searches": 500, "enrichments": 300},
    "command": {"searches": 2000, "enrichments": 1500},
}


def get_tier_limits(tier: str) -> dict:
    """Get limits for a tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["scout"])


def update_user_tier(db: Session, user: User, tier: str) -> User:
    """Update user's tier and limits."""
    limits = get_tier_limits(tier)
    user.tier = tier
    user.searches_limit = limits["searches"]
    user.enrichments_limit = limits["enrichments"]
    db.commit()
    db.refresh(user)
    return user
