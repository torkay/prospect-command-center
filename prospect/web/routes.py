"""FastAPI routes for web UI."""

import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from prospect.web.state import job_manager, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter()


def get_templates(request: Request):
    """Get templates from app state."""
    return request.app.state.templates


# ============================================================================
# Pages
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main search page."""
    templates = get_templates(request)

    # Check if APIs are configured
    has_serpapi = bool(os.environ.get("SERPAPI_KEY"))
    has_sheets = bool(
        os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or
        os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
    )

    return templates.TemplateResponse(request, "index.html", {
        "has_serpapi": has_serpapi,
        "has_sheets": has_sheets,
    })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    templates = get_templates(request)

    serpapi_key = os.environ.get("SERPAPI_KEY", "")
    masked_key = serpapi_key[:8] + "..." if serpapi_key else ""

    return templates.TemplateResponse(request, "settings.html", {
        "serpapi_key": masked_key,
        "has_sheets": bool(
            os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or
            os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
        ),
    })


# ============================================================================
# Search API
# ============================================================================

@router.post("/search", response_class=HTMLResponse)
async def start_search(
    request: Request,
    background_tasks: BackgroundTasks,
    business_type: str = Form(...),
    location: str = Form(...),
    limit: int = Form(20),
):
    """Start a new prospect search."""
    templates = get_templates(request)

    # Validate inputs
    if not business_type.strip():
        return templates.TemplateResponse(request, "partials/error.html", {
            "error": "Business type is required",
        })

    if not location.strip():
        return templates.TemplateResponse(request, "partials/error.html", {
            "error": "Location is required",
        })

    limit = max(1, min(100, limit))  # Clamp to 1-100

    # Create job
    job = await job_manager.create_job(
        business_type=business_type.strip(),
        location=location.strip(),
        limit=limit,
    )

    # Start background task
    background_tasks.add_task(run_search_job, job.id)

    # Return progress partial (HTMX will poll for updates)
    return templates.TemplateResponse(request, "partials/progress.html", {
        "job": job,
    })


@router.get("/search/{job_id}/status", response_class=HTMLResponse)
async def search_status(request: Request, job_id: str):
    """Get current status of a search job (polled by HTMX)."""
    templates = get_templates(request)

    job = await job_manager.get_job(job_id)
    if not job:
        return templates.TemplateResponse(request, "partials/error.html", {
            "error": "Search not found",
        })

    # If complete, return results
    if job.status == JobStatus.COMPLETE:
        return templates.TemplateResponse(request, "partials/results.html", {
            "job": job,
            "prospects": job.results,
        })

    # If error, return error message
    if job.status == JobStatus.ERROR:
        return templates.TemplateResponse(request, "partials/error.html", {
            "error": job.error or "An error occurred",
        })

    # Otherwise, return progress (HTMX will continue polling)
    return templates.TemplateResponse(request, "partials/progress.html", {
        "job": job,
    })


@router.get("/search/{job_id}/export/csv")
async def export_csv(job_id: str):
    """Export search results as CSV."""
    job = await job_manager.get_job(job_id)
    if not job or job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=404, detail="Results not found")

    from prospect.export import export_csv_string

    csv_content = export_csv_string(job.results)

    filename = f"prospects_{job.business_type.replace(' ', '_')}_{job.location.replace(' ', '_')}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/search/{job_id}/export/sheets", response_class=HTMLResponse)
async def export_sheets(request: Request, job_id: str):
    """Export search results to Google Sheets."""
    templates = get_templates(request)

    job = await job_manager.get_job(job_id)
    if not job or job.status != JobStatus.COMPLETE:
        return templates.TemplateResponse(request, "partials/error.html", {
            "error": "Results not found",
        })

    try:
        from prospect.sheets import SheetsExporter

        exporter = SheetsExporter()
        sheet_name = f"Prospects - {job.business_type} in {job.location}"
        url = exporter.export(job.results, name=sheet_name)

        return templates.TemplateResponse(request, "partials/sheets_success.html", {
            "url": url,
        })

    except Exception as e:
        return templates.TemplateResponse(request, "partials/error.html", {
            "error": f"Google Sheets export failed: {e}",
        })


# ============================================================================
# Background Task
# ============================================================================

async def run_search_job(job_id: str):
    """Execute the search pipeline in background."""
    job = await job_manager.get_job(job_id)
    if not job:
        return

    try:
        # Import scraper components
        from prospect.scraper.serpapi import SerpAPIClient, AuthenticationError
        from prospect.dedup import deduplicate_serp_results
        from prospect.enrichment.crawler import WebsiteCrawler
        from prospect.scoring import calculate_fit_score, calculate_opportunity_score, generate_opportunity_notes
        from prospect.config import ScraperConfig

        # Phase 1: Search
        await job_manager.update_job(
            job_id,
            status=JobStatus.SEARCHING,
            progress_message="Searching Google..."
        )

        # Use SerpAPI
        try:
            client = SerpAPIClient()
            serp_results = client.search(job.business_type, job.location, job.limit)
            client.close()
        except AuthenticationError as e:
            await job_manager.update_job(
                job_id,
                status=JobStatus.ERROR,
                error=f"SerpAPI not configured: {e}"
            )
            return
        except Exception as e:
            await job_manager.update_job(
                job_id,
                status=JobStatus.ERROR,
                error=f"Search failed: {e}"
            )
            return

        # Deduplicate (pass location for phone validation)
        prospects = deduplicate_serp_results(serp_results, location=job.location)

        await job_manager.update_job(
            job_id,
            progress_message=f"Found {len(prospects)} prospects",
            progress_total=len(prospects),
        )

        if not prospects:
            await job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETE,
                results=[],
                progress_message="No prospects found"
            )
            return

        # Small delay to show progress
        await asyncio.sleep(0.5)

        # Phase 2: Enrich
        await job_manager.update_job(
            job_id,
            status=JobStatus.ENRICHING,
            progress=0,
            progress_message="Analyzing websites..."
        )

        config = ScraperConfig()

        async with WebsiteCrawler(config) as crawler:
            for i, prospect in enumerate(prospects):
                # Update progress
                await job_manager.update_job(
                    job_id,
                    progress=i + 1,
                    progress_message=f"Analyzing {prospect.name[:30]}..."
                )

                # Enrich
                try:
                    await crawler.enrich_prospect(prospect)
                except Exception as e:
                    logger.debug("Failed to enrich %s: %s", prospect.name, e)

                # Small delay between requests
                await asyncio.sleep(0.1)

        # Phase 3: Score
        await job_manager.update_job(
            job_id,
            status=JobStatus.SCORING,
            progress_message="Scoring prospects..."
        )

        for prospect in prospects:
            prospect.fit_score = calculate_fit_score(prospect)
            prospect.opportunity_score = calculate_opportunity_score(prospect)
            prospect.priority_score = (prospect.fit_score + prospect.opportunity_score) / 2
            prospect.opportunity_notes = generate_opportunity_notes(prospect)

        # Sort by priority score
        prospects.sort(key=lambda p: p.priority_score, reverse=True)

        # Limit results
        prospects = prospects[:job.limit]

        # Phase 4: Complete
        await job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETE,
            results=prospects,
            progress_message="Complete!"
        )

    except Exception as e:
        logger.exception(f"Search job {job_id} failed")
        await job_manager.update_job(
            job_id,
            status=JobStatus.ERROR,
            error=str(e),
        )
