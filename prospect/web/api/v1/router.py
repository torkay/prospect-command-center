"""API v1 router."""

from fastapi import APIRouter

from prospect.web.api.v1 import search, jobs, config

router = APIRouter(prefix="/api/v1")

router.include_router(search.router, tags=["search"])
router.include_router(jobs.router, tags=["jobs"])
router.include_router(config.router, tags=["config"])
