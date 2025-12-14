"""Job management endpoints."""

import csv
import io
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from prospect.web.state import job_manager, JobStatus

router = APIRouter()


class JobSummary(BaseModel):
    """Job summary for list view."""
    id: str
    status: str
    business_type: str
    location: str
    progress: int
    progress_total: int
    message: str
    created_at: str
    duration_ms: Optional[int] = None


class JobStats(BaseModel):
    """Job statistics."""
    total_found: int
    after_filters: int
    avg_fit_score: float
    avg_opportunity_score: float
    sources: dict


class JobDetail(BaseModel):
    """Full job details including results."""
    id: str
    status: str
    business_type: str
    location: str
    progress: int
    progress_total: int
    message: str
    created_at: str
    duration_ms: Optional[int] = None
    request: Optional[dict] = None
    results: Optional[List[dict]] = None
    stats: Optional[dict] = None
    error: Optional[str] = None


@router.get("/jobs", response_model=List[JobSummary])
async def list_jobs(
    limit: int = Query(default=20, le=100),
    status: Optional[str] = None,
):
    """List recent jobs."""
    jobs = await job_manager.list_jobs(limit=limit, status=status)

    return [
        JobSummary(
            id=j.id,
            status=j.status.value,
            business_type=j.business_type,
            location=j.location,
            progress=j.progress,
            progress_total=j.progress_total,
            message=j.progress_message or "",
            created_at=j.created_at.isoformat(),
            duration_ms=j.duration_ms,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(job_id: str):
    """Get job details including results."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate stats if complete
    stats = None
    results_list = None

    if job.status == JobStatus.COMPLETE and job.results:
        results = job.results
        results_list = [r.to_dict() for r in results]
        stats = {
            "total_found": len(results),
            "after_filters": len(results),
            "avg_fit_score": sum(r.fit_score for r in results) / len(results) if results else 0,
            "avg_opportunity_score": sum(r.opportunity_score for r in results) / len(results) if results else 0,
            "sources": {
                "ads": sum(1 for r in results if r.found_in_ads),
                "maps": sum(1 for r in results if r.found_in_maps),
                "organic": sum(1 for r in results if r.found_in_organic),
            }
        }

    return JobDetail(
        id=job.id,
        status=job.status.value,
        business_type=job.business_type,
        location=job.location,
        progress=job.progress,
        progress_total=job.progress_total,
        message=job.progress_message or "",
        created_at=job.created_at.isoformat(),
        duration_ms=job.duration_ms,
        request=job.config,
        results=results_list,
        stats=stats,
        error=job.error,
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str):
    """Delete/cancel a job."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await job_manager.delete_job(job_id)


@router.get("/jobs/{job_id}/results")
async def get_results(
    job_id: str,
    format: str = Query(default="json", pattern="^(json|csv|jsonl)$"),
    min_priority: Optional[float] = None,
    limit: Optional[int] = None,
):
    """
    Get job results in specified format.

    Supports streaming for large result sets.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail=f"Job status: {job.status.value}")

    results = job.results or []

    # Apply filters
    if min_priority:
        results = [r for r in results if r.priority_score >= min_priority]
    if limit:
        results = results[:limit]

    # Format output
    if format == "json":
        return {"count": len(results), "results": [r.to_dict() for r in results]}

    elif format == "jsonl":
        def generate():
            for r in results:
                yield json.dumps(r.to_dict()) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f"attachment; filename=prospects_{job_id}.jsonl"}
        )

    elif format == "csv":
        output = io.StringIO()
        if results:
            # Get all keys from first result
            first_dict = results[0].to_dict()
            # Flatten nested dicts for CSV
            fieldnames = []
            for k, v in first_dict.items():
                if isinstance(v, dict):
                    fieldnames.extend([f"{k}_{sk}" for sk in v.keys()])
                elif isinstance(v, list):
                    fieldnames.append(k)
                else:
                    fieldnames.append(k)

            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for r in results:
                row = {}
                d = r.to_dict()
                for k, v in d.items():
                    if isinstance(v, dict):
                        for sk, sv in v.items():
                            row[f"{k}_{sk}"] = sv
                    elif isinstance(v, list):
                        row[k] = ";".join(str(x) for x in v)
                    else:
                        row[k] = v
                writer.writerow(row)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=prospects_{job_id}.csv"}
        )


@router.post("/jobs/{job_id}/export/sheets")
async def export_to_sheets(job_id: str):
    """Export job results to Google Sheets."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail=f"Job status: {job.status.value}")

    if not job.results:
        raise HTTPException(status_code=400, detail="No results to export")

    try:
        from prospect.sheets import SheetsExporter

        exporter = SheetsExporter()
        sheet_name = f"Prospects - {job.business_type} in {job.location}"
        url = exporter.export(job.results, name=sheet_name)

        return {"url": url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
