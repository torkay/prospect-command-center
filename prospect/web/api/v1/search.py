"""Search endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from prospect.web.state import job_manager
from prospect.web.api.v1.models import SearchRequest, JobResponse

router = APIRouter()


@router.post("/search", response_model=JobResponse, status_code=202)
async def create_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new prospect search job.

    Returns immediately with job ID. Poll /jobs/{id} for status
    or connect to WebSocket /ws/jobs/{id} for real-time updates.
    """
    from prospect.web.tasks import run_search_task

    job = await job_manager.create_job(
        business_type=request.business_type,
        location=request.location,
        limit=request.limit,
        config=request.model_dump(),
    )

    background_tasks.add_task(run_search_task, job.id, request)

    return JobResponse(
        id=job.id,
        status=job.status.value,
        message="Job created"
    )


@router.post("/search/sync")
async def search_sync(request: SearchRequest):
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

    return {
        "count": len(results),
        "results": [r.to_dict() for r in results]
    }
