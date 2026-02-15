"""Search endpoints with depth control."""

from typing import List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from prospect.web.state import job_manager
from prospect.web.api.v1.models import (
    SearchRequest,
    JobResponse,
    SearchEstimate,
    SearchConfigResponse,
    SearchDepth,
)
from prospect.web.database import get_db, Session, SearchConfig, User
from prospect.web.auth import get_current_user
from prospect.web.api.v1.usage import (
    require_search_limit,
    increment_search_usage,
    get_usage_summary,
)

router = APIRouter()


# Prospect ranges by depth
PROSPECT_RANGES = {
    "quick": "5-15",
    "standard": "20-40",
    "deep": "50-100",
    "exhaustive": "100-200+",
}


def get_search_config(db: Session, depth: str) -> dict:
    """Get search config dict by depth name."""
    config = db.query(SearchConfig).filter(SearchConfig.name == depth).first()
    if not config:
        # Fall back to standard
        config = db.query(SearchConfig).filter(SearchConfig.name == "standard").first()

    if config:
        return {
            "organic_pages": config.organic_pages,
            "maps_pages": config.maps_pages,
            "use_query_variations": config.use_query_variations,
            "query_variations": config.query_variations or [],
            "use_location_expansion": config.use_location_expansion,
            "expansion_radius_km": config.expansion_radius_km,
            "max_locations": config.max_locations,
            "search_organic": config.search_organic,
            "search_maps": config.search_maps,
            "search_local_services": config.search_local_services,
            "max_api_calls": config.max_api_calls,
            "estimated_cost_cents": config.estimated_cost_cents,
        }

    # Hard-coded fallback
    return {
        "organic_pages": 2,
        "maps_pages": 1,
        "use_query_variations": True,
        "query_variations": ["{business_type} services", "{business_type} near me"],
        "use_location_expansion": False,
        "expansion_radius_km": 0,
        "max_locations": 1,
        "search_organic": True,
        "search_maps": True,
        "search_local_services": False,
        "max_api_calls": 5,
        "estimated_cost_cents": 5,
    }


@router.post("/search/estimate", response_model=SearchEstimate)
def estimate_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Estimate search scope and cost before running.

    Returns query expansion, location expansion, and cost estimate.
    """
    # Heavy import (Playwright stack) deferred to keep app startup fast.
    from prospect.scraper.orchestrator import SearchOrchestrator

    config = get_search_config(db, request.depth.value)
    orchestrator = SearchOrchestrator()

    plan = orchestrator.plan_search(
        business_type=request.business_type,
        location=request.location,
        config=config,
    )

    warning = None
    if request.depth == SearchDepth.exhaustive:
        warning = "Exhaustive searches use significant API credits. Consider 'deep' for most cases."

    return SearchEstimate(
        queries=plan.queries,
        locations=plan.locations,
        total_api_calls=plan.total_api_calls,
        estimated_cost_cents=plan.estimated_cost_cents,
        estimated_prospects=PROSPECT_RANGES.get(request.depth.value, "20-40"),
        warning=warning,
    )


@router.get("/search/configs", response_model=List[SearchConfigResponse])
def list_search_configs(db: Session = Depends(get_db)):
    """List available search configurations."""
    configs = db.query(SearchConfig).all()

    return [
        SearchConfigResponse(
            name=c.name,
            description=c.description or "",
            estimated_cost_cents=c.estimated_cost_cents,
            max_api_calls=c.max_api_calls,
            estimated_prospects=PROSPECT_RANGES.get(c.name, "20-40"),
        )
        for c in configs
    ]


@router.post("/search", response_model=JobResponse, status_code=202)
async def create_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a new prospect search job.

    Returns immediately with job ID. Poll /jobs/{id} for status
    or connect to WebSocket /ws/jobs/{id} for real-time updates.
    """
    from prospect.web.tasks import run_search_task

    # Check usage limits before starting search
    require_search_limit(db, current_user)

    # Get search config for depth
    search_config = get_search_config(db, request.depth.value)

    job = await job_manager.create_job(
        business_type=request.business_type,
        location=request.location,
        limit=request.limit,
        config={
            **request.model_dump(),
            "search_config": search_config,
            "user_id": current_user.id,
        },
    )

    # Increment search usage now that job is created
    increment_search_usage(db, current_user)

    # Get updated usage summary for response
    usage = get_usage_summary(db, current_user)

    background_tasks.add_task(run_search_task, job.id, request)

    return JobResponse(
        id=job.id,
        status=job.status.value,
        message="Job created",
        depth=request.depth.value,
        searches_remaining=usage["searches_remaining"],
    )


@router.post("/search/sync")
async def search_sync(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synchronous search - blocks until complete.

    Use for small searches or scripting. For larger searches,
    use async /search endpoint.
    """
    if request.limit > 10:
        raise HTTPException(
            status_code=400,
            detail="Use async /search for limit > 10"
        )

    # Check usage limits before starting search
    require_search_limit(db, current_user)

    from prospect.api import search_prospects

    results = search_prospects(
        business_type=request.business_type,
        location=request.location,
        limit=request.limit,
        skip_enrichment=request.skip_enrichment,
        min_fit=request.filters.min_fit,
        min_opportunity=request.filters.min_opportunity,
        min_priority=request.filters.min_priority,
        fit_weight=request.scoring.fit_weight,
        opportunity_weight=request.scoring.opportunity_weight,
    )

    # Increment search usage after successful search
    increment_search_usage(db, current_user)

    # Get updated usage summary for response
    usage = get_usage_summary(db, current_user)

    return {
        "count": len(results),
        "results": [r.to_dict() for r in results],
        "searches_remaining": usage["searches_remaining"],
    }
