"""Prospect management endpoints - for workflow tracking."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from datetime import datetime

from prospect.web.database import get_db, Prospect

router = APIRouter(prefix="/prospects", tags=["prospects"])


class ProspectUpdate(BaseModel):
    """Update prospect request."""
    status: Optional[str] = None
    user_notes: Optional[str] = None
    follow_up_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


class ProspectResponse(BaseModel):
    """Prospect response model."""
    model_config = {"from_attributes": True}

    id: int
    search_id: Optional[int]
    domain: Optional[str]
    name: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    emails: Optional[str]
    address: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    found_in_ads: bool
    found_in_maps: bool
    found_in_organic: bool
    fit_score: int
    opportunity_score: int
    priority_score: float
    opportunity_notes: Optional[str]
    status: str
    user_notes: Optional[str]
    tags: List[str]
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    seen_count: int


class ProspectStats(BaseModel):
    """Prospect statistics."""
    total: int
    status_breakdown: dict
    avg_fit_score: float
    avg_opportunity_score: float
    avg_priority_score: float
    with_email: int
    with_phone: int
    contact_rate: float


@router.get("", response_model=List[ProspectResponse])
def list_prospects(
    db: Session = Depends(get_db),
    search_id: Optional[int] = None,
    status: Optional[str] = None,
    min_priority: Optional[float] = None,
    min_fit: Optional[int] = None,
    min_opportunity: Optional[int] = None,
    has_email: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: str = Query(default="priority_score", pattern="^(priority_score|fit_score|opportunity_score|first_seen_at|name)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    """
    List prospects with filtering and sorting.

    Supports workflow management by filtering on status, tags, etc.
    """
    query = db.query(Prospect)

    # Filters
    if search_id:
        query = query.filter(Prospect.search_id == search_id)
    if status:
        query = query.filter(Prospect.status == status)
    if min_priority:
        query = query.filter(Prospect.priority_score >= min_priority)
    if min_fit:
        query = query.filter(Prospect.fit_score >= min_fit)
    if min_opportunity:
        query = query.filter(Prospect.opportunity_score >= min_opportunity)
    if has_email:
        query = query.filter(Prospect.emails.isnot(None), Prospect.emails != "")
    if has_phone:
        query = query.filter(Prospect.phone.isnot(None), Prospect.phone != "")
    if q:
        query = query.filter(
            or_(
                Prospect.name.ilike(f"%{q}%"),
                Prospect.domain.ilike(f"%{q}%"),
            )
        )

    # Sorting
    sort_column = getattr(Prospect, sort_by, Prospect.priority_score)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    prospects = query.offset(skip).limit(limit).all()

    # Convert to response format, handling null tags
    result = []
    for p in prospects:
        result.append(ProspectResponse(
            id=p.id,
            search_id=p.search_id,
            domain=p.domain,
            name=p.name,
            website=p.website,
            phone=p.phone,
            emails=p.emails,
            address=p.address,
            rating=p.rating,
            review_count=p.review_count,
            found_in_ads=p.found_in_ads,
            found_in_maps=p.found_in_maps,
            found_in_organic=p.found_in_organic,
            fit_score=p.fit_score,
            opportunity_score=p.opportunity_score,
            priority_score=p.priority_score,
            opportunity_notes=p.opportunity_notes,
            status=p.status,
            user_notes=p.user_notes,
            tags=p.tags or [],
            first_seen_at=p.first_seen_at,
            last_seen_at=p.last_seen_at,
            seen_count=p.seen_count,
        ))
    return result


@router.get("/stats", response_model=ProspectStats)
def get_prospect_stats(
    db: Session = Depends(get_db),
    search_id: Optional[int] = None,
):
    """Get aggregate stats for prospects - returns all status counts explicitly."""
    base_query = db.query(Prospect)
    if search_id:
        base_query = base_query.filter(Prospect.search_id == search_id)

    total = base_query.count()

    # Build status breakdown with all statuses (including zeros)
    all_statuses = ['new', 'qualified', 'contacted', 'meeting', 'won', 'lost', 'skipped']
    status_breakdown = {}
    for status in all_statuses:
        count_query = db.query(Prospect).filter(Prospect.status == status)
        if search_id:
            count_query = count_query.filter(Prospect.search_id == search_id)
        status_breakdown[status] = count_query.count()

    if total == 0:
        return ProspectStats(
            total=0,
            status_breakdown=status_breakdown,
            avg_fit_score=0,
            avg_opportunity_score=0,
            avg_priority_score=0,
            with_email=0,
            with_phone=0,
            contact_rate=0,
        )

    # Score averages
    avg_query = db.query(
        func.avg(Prospect.fit_score),
        func.avg(Prospect.opportunity_score),
        func.avg(Prospect.priority_score)
    )
    if search_id:
        avg_query = avg_query.filter(Prospect.search_id == search_id)
    averages = avg_query.first()

    avg_fit = averages[0] or 0
    avg_opp = averages[1] or 0
    avg_pri = averages[2] or 0

    # With contact info
    email_query = base_query.filter(Prospect.emails.isnot(None), Prospect.emails != "")
    with_email = email_query.count()

    phone_query = base_query.filter(Prospect.phone.isnot(None), Prospect.phone != "")
    with_phone = phone_query.count()

    return ProspectStats(
        total=total,
        status_breakdown=status_breakdown,
        avg_fit_score=round(float(avg_fit), 1),
        avg_opportunity_score=round(float(avg_opp), 1),
        avg_priority_score=round(float(avg_pri), 1),
        with_email=with_email,
        with_phone=with_phone,
        contact_rate=round(with_email / total * 100, 1) if total > 0 else 0,
    )


@router.get("/{prospect_id}", response_model=ProspectResponse)
def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
):
    """Get a single prospect by ID."""
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    return ProspectResponse(
        id=prospect.id,
        search_id=prospect.search_id,
        domain=prospect.domain,
        name=prospect.name,
        website=prospect.website,
        phone=prospect.phone,
        emails=prospect.emails,
        address=prospect.address,
        rating=prospect.rating,
        review_count=prospect.review_count,
        found_in_ads=prospect.found_in_ads,
        found_in_maps=prospect.found_in_maps,
        found_in_organic=prospect.found_in_organic,
        fit_score=prospect.fit_score,
        opportunity_score=prospect.opportunity_score,
        priority_score=prospect.priority_score,
        opportunity_notes=prospect.opportunity_notes,
        status=prospect.status,
        user_notes=prospect.user_notes,
        tags=prospect.tags or [],
        first_seen_at=prospect.first_seen_at,
        last_seen_at=prospect.last_seen_at,
        seen_count=prospect.seen_count,
    )


@router.patch("/{prospect_id}", response_model=ProspectResponse)
def update_prospect(
    prospect_id: int,
    update: ProspectUpdate,
    db: Session = Depends(get_db),
):
    """
    Update prospect workflow status.

    Used for:
    - Marking as qualified/contacted/won/lost
    - Adding notes
    - Setting follow-up reminders
    - Tagging
    """
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    if update.status is not None:
        prospect.status = update.status
        if update.status == "contacted":
            prospect.contacted_at = datetime.utcnow()

    if update.user_notes is not None:
        prospect.user_notes = update.user_notes

    if update.follow_up_at is not None:
        prospect.follow_up_at = update.follow_up_at

    if update.tags is not None:
        prospect.tags = update.tags

    db.commit()
    db.refresh(prospect)

    return ProspectResponse(
        id=prospect.id,
        search_id=prospect.search_id,
        domain=prospect.domain,
        name=prospect.name,
        website=prospect.website,
        phone=prospect.phone,
        emails=prospect.emails,
        address=prospect.address,
        rating=prospect.rating,
        review_count=prospect.review_count,
        found_in_ads=prospect.found_in_ads,
        found_in_maps=prospect.found_in_maps,
        found_in_organic=prospect.found_in_organic,
        fit_score=prospect.fit_score,
        opportunity_score=prospect.opportunity_score,
        priority_score=prospect.priority_score,
        opportunity_notes=prospect.opportunity_notes,
        status=prospect.status,
        user_notes=prospect.user_notes,
        tags=prospect.tags or [],
        first_seen_at=prospect.first_seen_at,
        last_seen_at=prospect.last_seen_at,
        seen_count=prospect.seen_count,
    )


@router.post("/{prospect_id}/skip", response_model=ProspectResponse)
def skip_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
):
    """Quick action to skip a prospect."""
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    prospect.status = "skipped"
    db.commit()
    db.refresh(prospect)

    return ProspectResponse(
        id=prospect.id,
        search_id=prospect.search_id,
        domain=prospect.domain,
        name=prospect.name,
        website=prospect.website,
        phone=prospect.phone,
        emails=prospect.emails,
        address=prospect.address,
        rating=prospect.rating,
        review_count=prospect.review_count,
        found_in_ads=prospect.found_in_ads,
        found_in_maps=prospect.found_in_maps,
        found_in_organic=prospect.found_in_organic,
        fit_score=prospect.fit_score,
        opportunity_score=prospect.opportunity_score,
        priority_score=prospect.priority_score,
        opportunity_notes=prospect.opportunity_notes,
        status=prospect.status,
        user_notes=prospect.user_notes,
        tags=prospect.tags or [],
        first_seen_at=prospect.first_seen_at,
        last_seen_at=prospect.last_seen_at,
        seen_count=prospect.seen_count,
    )


class BulkUpdateRequest(BaseModel):
    """Bulk update request."""
    prospect_ids: List[int]
    status: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/bulk-update")
def bulk_update_prospects(
    request: BulkUpdateRequest,
    db: Session = Depends(get_db),
):
    """Bulk update multiple prospects."""
    updated = 0
    for pid in request.prospect_ids:
        prospect = db.query(Prospect).filter(Prospect.id == pid).first()
        if prospect:
            if request.status:
                prospect.status = request.status
                if request.status == "contacted":
                    prospect.contacted_at = datetime.utcnow()
            if request.tags is not None:
                prospect.tags = request.tags
            updated += 1

    db.commit()
    return {"updated": updated}


@router.delete("/{prospect_id}", status_code=204)
def delete_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
):
    """Delete a prospect."""
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    db.delete(prospect)
    db.commit()
