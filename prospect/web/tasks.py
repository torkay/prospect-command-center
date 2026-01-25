"""Background task execution for search jobs."""

import asyncio
import logging
from datetime import datetime

from prospect.web.state import job_manager, JobStatus
from prospect.web.api.v1.models import SearchRequest
from prospect.web.database import SessionLocal, Search, User, save_prospects_from_results
from prospect.web.api.v1.usage import increment_enrichment_usage

logger = logging.getLogger(__name__)


async def run_search_task(job_id: str, request: SearchRequest):
    """Execute the search pipeline in background."""
    job = await job_manager.get_job(job_id)
    if not job:
        return

    try:
        # Import scraper components
        from prospect.scraper.serpapi import SerpAPIClient, AuthenticationError
        from prospect.scraper.orchestrator import SearchOrchestrator
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
        search_config = job.config.get("search_config") if job.config else None

        # Phase 1: Search
        await job_manager.update_job(
            job_id,
            status=JobStatus.SEARCHING,
            progress_message="Searching Google..."
        )

        # Use orchestrator for tiered search if config available
        if search_config and request.depth.value != "quick":
            # Use orchestrator for standard/deep/exhaustive
            try:
                orchestrator = SearchOrchestrator()
                prospects = []

                async for progress in orchestrator.execute_search(
                    business_type=request.business_type,
                    location=request.location,
                    config=search_config,
                ):
                    # Update job progress
                    if progress.phase == "searching":
                        msg = f"Searching: {progress.current_query}"
                        if progress.current_location != request.location:
                            msg += f" in {progress.current_location}"
                        if progress.current_page > 1:
                            msg += f" (page {progress.current_page})"

                        await job_manager.update_job(
                            job_id,
                            progress_message=msg,
                            progress=progress.completed_api_calls,
                            progress_total=progress.total_api_calls,
                        )
                    elif progress.phase == "deduplicating":
                        await job_manager.update_job(
                            job_id,
                            progress_message=f"Deduplicating {progress.total_prospects} results..."
                        )
                    elif progress.phase == "complete":
                        prospects = progress.results

                orchestrator.close()

            except AuthenticationError as e:
                await job_manager.update_job(
                    job_id,
                    status=JobStatus.ERROR,
                    error=f"SerpAPI not configured: {e}"
                )
                return
            except Exception as e:
                logger.exception("Orchestrator search failed")
                await job_manager.update_job(
                    job_id,
                    status=JobStatus.ERROR,
                    error=f"Search failed: {e}"
                )
                return
        else:
            # Use simple SerpAPI for quick search
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

            # Deduplicate (pass location for phone validation)
            prospects = deduplicate_serp_results(serp_results, location=request.location)

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
                progress_message="Analysing websites..."
            )

            config = ScraperConfig()

            async with WebsiteCrawler(config) as crawler:
                for i, prospect in enumerate(prospects):
                    # Update progress
                    await job_manager.update_job(
                        job_id,
                        progress=i + 1,
                        progress_message=f"Analysing {prospect.name[:30]}..."
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

        # Phase 4: Save to database
        await job_manager.update_job(
            job_id,
            progress_message="Saving results..."
        )

        # Get search_id and campaign_id from job config
        search_id = job.config.get("search_id") if job.config else None
        campaign_id = job.config.get("campaign_id") if job.config else None

        # Create or update search record
        db = SessionLocal()
        try:
            if search_id:
                # Update existing search record (from campaign run)
                search = db.query(Search).filter(Search.id == search_id).first()
                if search:
                    search.status = "complete"
                    search.total_found = len(prospects)
                    search.avg_fit_score = sum(p.fit_score for p in prospects) / len(prospects) if prospects else 0
                    search.avg_opportunity_score = sum(p.opportunity_score for p in prospects) / len(prospects) if prospects else 0
                    if job.created_at:
                        search.duration_ms = int((datetime.now() - job.created_at).total_seconds() * 1000)
                    db.commit()
            else:
                # Create new search record
                search = Search(
                    campaign_id=campaign_id,
                    business_type=request.business_type,
                    location=request.location,
                    query=f"{request.business_type} in {request.location}",
                    status="complete",
                    total_found=len(prospects),
                    avg_fit_score=sum(p.fit_score for p in prospects) / len(prospects) if prospects else 0,
                    avg_opportunity_score=sum(p.opportunity_score for p in prospects) / len(prospects) if prospects else 0,
                    duration_ms=int((datetime.now() - job.created_at).total_seconds() * 1000) if job.created_at else None,
                )
                db.add(search)
                db.commit()
                db.refresh(search)
                search_id = search.id

            # Save prospects to database
            if prospects and search_id:
                save_prospects_from_results(db, search_id, prospects)
                logger.info(f"Saved {len(prospects)} prospects to database for search {search_id}")

            # Increment enrichment usage if enrichment was performed
            if not request.skip_enrichment and prospects:
                user_id = job.config.get("user_id") if job.config else None
                if user_id:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        enrichment_count = len(prospects)
                        increment_enrichment_usage(db, user, enrichment_count)
                        logger.info(f"Incremented enrichment usage by {enrichment_count} for user {user_id}")
        except Exception as e:
            logger.exception(f"Failed to save search results to database: {e}")
        finally:
            db.close()

        # Phase 5: Complete
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
