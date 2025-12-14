"""Background task execution for search jobs."""

import asyncio
import logging

from prospect.web.state import job_manager, JobStatus
from prospect.web.api.v1.models import SearchRequest

logger = logging.getLogger(__name__)


async def run_search_task(job_id: str, request: SearchRequest):
    """Execute the search pipeline in background."""
    job = await job_manager.get_job(job_id)
    if not job:
        return

    try:
        # Import scraper components
        from prospect.scraper.serpapi import SerpAPIClient, AuthenticationError
        from prospect.dedup import deduplicate_serp_results
        from prospect.enrichment.crawler import WebsiteCrawler
        from prospect.scoring import (
            calculate_fit_score,
            calculate_opportunity_score,
            generate_opportunity_notes,
        )
        from prospect.config import ScraperConfig

        # Extract config
        filters = request.filters
        scoring = request.scoring

        # Phase 1: Search
        await job_manager.update_job(
            job_id,
            status=JobStatus.SEARCHING,
            progress_message="Searching Google..."
        )

        # Use SerpAPI
        try:
            client = SerpAPIClient()
            serp_results = client.search(
                request.business_type,
                request.location,
                request.limit
            )
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

        # Deduplicate
        prospects = deduplicate_serp_results(serp_results)

        # Apply domain exclusions
        if filters.exclude_domains:
            exclude_set = set(d.lower() for d in filters.exclude_domains)
            prospects = [
                p for p in prospects
                if not p.domain or p.domain.lower() not in exclude_set
            ]

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
        await asyncio.sleep(0.3)

        # Phase 2: Enrich (unless skipped)
        if not request.skip_enrichment:
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
                    await asyncio.sleep(0.05)

        # Phase 3: Score
        await job_manager.update_job(
            job_id,
            status=JobStatus.SCORING,
            progress_message="Scoring prospects..."
        )

        fit_weight = scoring.fit_weight
        opp_weight = scoring.opportunity_weight

        for prospect in prospects:
            prospect.fit_score = calculate_fit_score(prospect)
            prospect.opportunity_score = calculate_opportunity_score(prospect)
            prospect.priority_score = (
                prospect.fit_score * fit_weight +
                prospect.opportunity_score * opp_weight
            )
            prospect.opportunity_notes = generate_opportunity_notes(prospect)

        # Sort by priority score
        prospects.sort(key=lambda p: p.priority_score, reverse=True)

        # Apply score filters
        if filters.min_fit:
            prospects = [p for p in prospects if p.fit_score >= filters.min_fit]
        if filters.min_opportunity:
            prospects = [p for p in prospects if p.opportunity_score >= filters.min_opportunity]
        if filters.min_priority:
            prospects = [p for p in prospects if p.priority_score >= filters.min_priority]
        if filters.require_phone:
            prospects = [p for p in prospects if p.phone]
        if filters.require_email:
            prospects = [p for p in prospects if p.emails]

        # Limit results
        prospects = prospects[:request.limit]

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
