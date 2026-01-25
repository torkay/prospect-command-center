"""Campaign management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from prospect.web.database import get_db, Campaign, Search, User
from prospect.web.auth import get_current_user

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    """Create campaign request."""
    name: str
    business_type: str
    location: str
    limit: int = 20
    filters: dict = {}
    color: str = "blue"
    icon: str = "search"


class CampaignUpdate(BaseModel):
    """Update campaign request."""
    name: Optional[str] = None
    business_type: Optional[str] = None
    location: Optional[str] = None
    limit: Optional[int] = None
    filters: Optional[dict] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class CampaignResponse(BaseModel):
    """Campaign response model."""
    model_config = {"from_attributes": True}

    id: int
    name: str
    business_type: str
    location: str
    limit: int
    filters: dict
    color: str
    icon: str
    created_at: datetime
    last_run_at: Optional[datetime]
    run_count: int


@router.get("", response_model=List[CampaignResponse])
def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(default=50, le=100),
):
    """List all saved campaigns for the current user."""
    campaigns = db.query(Campaign).filter(
        Campaign.user_id == current_user.id
    ).order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
    return campaigns


@router.post("", response_model=CampaignResponse, status_code=201)
def create_campaign(
    campaign: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new campaign."""
    db_campaign = Campaign(
        user_id=current_user.id,
        name=campaign.name,
        business_type=campaign.business_type,
        location=campaign.location,
        limit=campaign.limit,
        filters=campaign.filters,
        color=campaign.color,
        icon=campaign.icon,
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get campaign by ID."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    update: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    db.delete(campaign)
    db.commit()


@router.post("/{campaign_id}/run")
async def run_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run a campaign search.

    Updates campaign metadata and starts a new search job.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Update campaign metadata
    campaign.last_run_at = datetime.utcnow()
    campaign.run_count += 1
    db.commit()

    # Create search record
    search = Search(
        user_id=current_user.id,
        campaign_id=campaign.id,
        business_type=campaign.business_type,
        location=campaign.location,
        query=f"{campaign.business_type} in {campaign.location}",
        status="pending",
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    # Trigger the search via the job manager
    from prospect.web.state import job_manager
    from prospect.web.api.v1.models import SearchRequest, Filters
    from prospect.web.tasks import run_search_task

    # Build filters from campaign
    filters = Filters(**campaign.filters) if campaign.filters else Filters()

    request = SearchRequest(
        business_type=campaign.business_type,
        location=campaign.location,
        limit=campaign.limit,
        filters=filters,
    )

    job = await job_manager.create_job(
        business_type=campaign.business_type,
        location=campaign.location,
        limit=campaign.limit,
        config={
            **request.model_dump(),
            "campaign_id": campaign.id,
            "search_id": search.id,
        },
    )

    background_tasks.add_task(run_search_task, job.id, request)

    return {
        "job_id": job.id,
        "campaign_id": campaign_id,
        "search_id": search.id,
        "message": "Campaign search started",
        "search_params": {
            "business_type": campaign.business_type,
            "location": campaign.location,
            "limit": campaign.limit,
        }
    }


@router.get("/{campaign_id}/searches")
def get_campaign_searches(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100),
):
    """Get search history for a campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    searches = (
        db.query(Search)
        .filter(Search.campaign_id == campaign_id)
        .order_by(Search.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": s.id,
            "status": s.status,
            "total_found": s.total_found,
            "avg_fit_score": s.avg_fit_score,
            "avg_opportunity_score": s.avg_opportunity_score,
            "created_at": s.created_at.isoformat(),
            "duration_ms": s.duration_ms,
            "error": s.error,
        }
        for s in searches
    ]
