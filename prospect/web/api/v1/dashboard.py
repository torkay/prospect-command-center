"""Dashboard and analytics endpoints."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from prospect.web.database import get_db, Search, Prospect, Campaign, User
from prospect.web.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dashboard summary stats.

    Shows:
    - Total prospects found
    - Pipeline breakdown
    - Recent activity
    - Top campaigns
    """
    # Total counts (filtered by user)
    total_prospects = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id
    ).count()
    total_searches = db.query(Search).filter(
        Search.user_id == current_user.id
    ).count()
    total_campaigns = db.query(Campaign).filter(
        Campaign.user_id == current_user.id
    ).count()

    # Pipeline breakdown (filtered by user)
    pipeline = db.query(
        Prospect.status,
        func.count(Prospect.id)
    ).join(Search).filter(
        Search.user_id == current_user.id
    ).group_by(Prospect.status).all()

    # Recent searches (last 7 days, filtered by user)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_searches = db.query(Search).filter(
        Search.user_id == current_user.id,
        Search.created_at >= week_ago
    ).count()

    # Prospects found this week (filtered by user)
    recent_prospects = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.first_seen_at >= week_ago
    ).count()

    # Top campaigns by run count (filtered by user)
    top_campaigns = db.query(Campaign).filter(
        Campaign.user_id == current_user.id
    ).order_by(
        Campaign.run_count.desc()
    ).limit(5).all()

    # Score distributions (filtered by user)
    high_priority = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.priority_score >= 60
    ).count()

    # Source breakdown (filtered by user)
    ads_count = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.found_in_ads == True
    ).count()
    maps_count = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.found_in_maps == True
    ).count()
    organic_count = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.found_in_organic == True
    ).count()

    return {
        "totals": {
            "prospects": total_prospects,
            "searches": total_searches,
            "campaigns": total_campaigns,
        },
        "pipeline": dict(pipeline),
        "this_week": {
            "searches": recent_searches,
            "prospects_found": recent_prospects,
        },
        "high_priority_prospects": high_priority,
        "sources": {
            "ads": ads_count,
            "maps": maps_count,
            "organic": organic_count,
        },
        "top_campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "business_type": c.business_type,
                "location": c.location,
                "run_count": c.run_count,
                "color": c.color,
            }
            for c in top_campaigns
        ],
    }


def get_relative_time(dt: datetime) -> str:
    """Get human-readable relative time."""
    now = datetime.now(timezone.utc)
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days}d ago"

    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"

    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes}m ago"

    return "just now"


@router.get("/activity")
def get_recent_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """Get recent activity feed - deduplicated."""
    # Fetch extra searches to account for deduplication (filtered by user)
    recent_searches = db.query(Search).filter(
        Search.user_id == current_user.id
    ).order_by(
        Search.created_at.desc()
    ).limit(limit * 2).all()

    # Deduplicate by (business_type, location, date)
    seen = set()
    activities = []

    for search in recent_searches:
        # Create dedup key (same search on same day = duplicate)
        date_str = search.created_at.strftime('%Y-%m-%d')
        dedup_key = (search.business_type, search.location, date_str)

        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        activities.append({
            "type": "search",
            "timestamp": search.created_at.isoformat(),
            "title": f"Search: {search.business_type} in {search.location}",
            "subtitle": f"Found {search.total_found} prospects",
            "relative_time": get_relative_time(search.created_at),
            "status": search.status,
            "search_id": search.id,
        })

        if len(activities) >= limit:
            break

    return activities


@router.get("/insights")
def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate actionable insights with proper grammar.

    Actions include filter information so the frontend can determine
    if the action is useful (applies filters vs. goes to same page).

    Examples:
    - "5 high-priority prospects need attention"
    - "1 prospect needs attention"
    """
    insights = []

    # High priority not contacted (filtered by user)
    high_priority_new = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.priority_score >= 60,
        Prospect.status == "new"
    ).count()

    if high_priority_new > 0:
        # Proper singular/plural grammar
        prospect_word = "prospect" if high_priority_new == 1 else "prospects"
        needs_word = "needs" if high_priority_new == 1 else "need"
        this_word = "This prospect has" if high_priority_new == 1 else "These prospects have"

        insights.append({
            "type": "action",
            "priority": "high",
            "icon": "alert-circle",
            "title": f"{high_priority_new} high-priority {prospect_word} {needs_word} attention",
            "description": f"{this_word} priority scores above 60 but haven't been contacted.",
            "action": "View high-priority",
            "action_url": "/prospects?status=new&min_priority=60",
            "action_filters": {"status": "new", "min_priority": "60"},
        })

    # Follow-ups due (filtered by user)
    follow_ups_due = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.follow_up_at <= datetime.now(timezone.utc),
        Prospect.status.notin_(["won", "lost", "skipped"])
    ).count()

    if follow_ups_due > 0:
        followup_word = "follow-up is" if follow_ups_due == 1 else "follow-ups are"
        insights.append({
            "type": "reminder",
            "priority": "medium",
            "icon": "clock",
            "title": f"{follow_ups_due} {followup_word} due",
            "description": "Prospects you scheduled to follow up with.",
            "action": "View follow-ups",
            "action_url": "/prospects?has_follow_up=true",
            "action_filters": {"has_follow_up": "true"},
        })

    # Prospects without email but high fit (filtered by user)
    no_email_high_fit = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.fit_score >= 70,
        (Prospect.emails.is_(None)) | (Prospect.emails == "")
    ).count()

    if no_email_high_fit > 0:
        prospect_word = "prospect" if no_email_high_fit == 1 else "prospects"
        is_word = "is" if no_email_high_fit == 1 else "are"
        these_word = "this high-fit prospect" if no_email_high_fit == 1 else "these high-fit prospects"
        insights.append({
            "type": "opportunity",
            "priority": "low",
            "icon": "mail",
            "title": f"{no_email_high_fit} good-fit {prospect_word} {is_word} missing email",
            "description": f"Consider finding emails manually for {these_word}.",
        })

    # No campaigns yet (filtered by user)
    campaign_count = db.query(Campaign).filter(
        Campaign.user_id == current_user.id
    ).count()
    if campaign_count == 0:
        search_count = db.query(Search).filter(
            Search.user_id == current_user.id
        ).count()
        if search_count > 0:
            insights.append({
                "type": "tip",
                "priority": "low",
                "icon": "folder-plus",
                "title": "Save your searches as campaigns",
                "description": "Create campaigns for searches you run regularly. One-click rerun.",
            })

    # Qualified but not contacted (filtered by user)
    qualified_not_contacted = db.query(Prospect).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.status == "qualified",
        Prospect.contacted_at.is_(None)
    ).count()

    if qualified_not_contacted > 0:
        prospect_word = "prospect" if qualified_not_contacted == 1 else "prospects"
        you_word = "this prospect" if qualified_not_contacted == 1 else "these prospects"
        insights.append({
            "type": "action",
            "priority": "medium",
            "icon": "star",
            "title": f"{qualified_not_contacted} qualified {prospect_word} waiting",
            "description": f"You've qualified {you_word} but haven't reached out yet.",
            "action": "View qualified",
            "action_url": "/prospects?status=qualified",
            "action_filters": {"status": "qualified"},
        })

    return insights


@router.get("/scores")
def get_score_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get score distribution for charts."""
    prospects = db.query(
        Prospect.fit_score,
        Prospect.opportunity_score,
        Prospect.priority_score
    ).join(Search).filter(
        Search.user_id == current_user.id
    ).all()

    # Create buckets for distribution
    fit_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    opp_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    pri_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

    def get_bucket(score):
        if score <= 20:
            return "0-20"
        elif score <= 40:
            return "21-40"
        elif score <= 60:
            return "41-60"
        elif score <= 80:
            return "61-80"
        else:
            return "81-100"

    for fit, opp, pri in prospects:
        fit_buckets[get_bucket(fit)] += 1
        opp_buckets[get_bucket(opp)] += 1
        pri_buckets[get_bucket(pri or 0)] += 1

    return {
        "fit_score": fit_buckets,
        "opportunity_score": opp_buckets,
        "priority_score": pri_buckets,
    }


@router.get("/timeline")
def get_search_timeline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30,
):
    """Get search/prospect counts over time."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Get searches per day (filtered by user)
    searches = db.query(
        func.date(Search.created_at).label("date"),
        func.count(Search.id).label("count")
    ).filter(
        Search.user_id == current_user.id,
        Search.created_at >= start_date
    ).group_by(
        func.date(Search.created_at)
    ).all()

    # Get prospects per day (filtered by user)
    prospects = db.query(
        func.date(Prospect.first_seen_at).label("date"),
        func.count(Prospect.id).label("count")
    ).join(Search).filter(
        Search.user_id == current_user.id,
        Prospect.first_seen_at >= start_date
    ).group_by(
        func.date(Prospect.first_seen_at)
    ).all()

    return {
        "searches": [{"date": str(s.date), "count": s.count} for s in searches],
        "prospects": [{"date": str(p.date), "count": p.count} for p in prospects],
    }
