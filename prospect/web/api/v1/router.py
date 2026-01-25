"""API v1 router."""

from fastapi import APIRouter

from prospect.web.api.v1 import auth, usage, search, jobs, config, campaigns, prospects, dashboard, billing

router = APIRouter(prefix="/api/v1")

# Auth routes (no auth required)
router.include_router(auth.router)

# Usage tracking
router.include_router(usage.router)

# Billing (Stripe)
router.include_router(billing.router)

# Protected routes
router.include_router(search.router, tags=["search"])
router.include_router(jobs.router, tags=["jobs"])
router.include_router(config.router, tags=["config"])
router.include_router(campaigns.router)
router.include_router(prospects.router)
router.include_router(dashboard.router)
