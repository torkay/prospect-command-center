"""Configuration endpoints."""

import os
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Runtime config (mutable during session)
_runtime_config = {
    "fit_weight": 0.4,
    "opportunity_weight": 0.6,
    "default_parallel": 3,
    "default_timeout": 10,
}

_start_time = time.time()


class ConfigResponse(BaseModel):
    """Configuration response."""
    serpapi_configured: bool
    sheets_configured: bool
    fit_weight: float
    opportunity_weight: float
    default_parallel: int
    default_timeout: int
    version: str


class ConfigUpdate(BaseModel):
    """Configuration update payload."""
    fit_weight: Optional[float] = None
    opportunity_weight: Optional[float] = None
    default_parallel: Optional[int] = None
    default_timeout: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    serpapi: bool
    sheets: bool
    version: str
    uptime_seconds: int


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration."""
    from prospect import __version__

    return ConfigResponse(
        serpapi_configured=bool(os.environ.get("SERPAPI_KEY")),
        sheets_configured=bool(
            os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or
            os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
        ),
        fit_weight=_runtime_config["fit_weight"],
        opportunity_weight=_runtime_config["opportunity_weight"],
        default_parallel=_runtime_config["default_parallel"],
        default_timeout=_runtime_config["default_timeout"],
        version=__version__,
    )


@router.patch("/config", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate):
    """
    Update runtime configuration.

    Changes are not persisted across restarts.
    For permanent changes, modify environment or config file.
    """
    if update.fit_weight is not None:
        if not 0 <= update.fit_weight <= 1:
            raise HTTPException(status_code=400, detail="fit_weight must be 0-1")
        _runtime_config["fit_weight"] = update.fit_weight

    if update.opportunity_weight is not None:
        if not 0 <= update.opportunity_weight <= 1:
            raise HTTPException(status_code=400, detail="opportunity_weight must be 0-1")
        _runtime_config["opportunity_weight"] = update.opportunity_weight

    if update.default_parallel is not None:
        if not 1 <= update.default_parallel <= 10:
            raise HTTPException(status_code=400, detail="default_parallel must be 1-10")
        _runtime_config["default_parallel"] = update.default_parallel

    if update.default_timeout is not None:
        if not 1 <= update.default_timeout <= 60:
            raise HTTPException(status_code=400, detail="default_timeout must be 1-60")
        _runtime_config["default_timeout"] = update.default_timeout

    return await get_config()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and API availability.
    """
    from prospect import __version__

    # Test SerpAPI
    serpapi_ok = False
    if os.environ.get("SERPAPI_KEY"):
        try:
            from prospect.scraper import SerpAPIClient
            client = SerpAPIClient()
            client.close()
            serpapi_ok = True
        except Exception:
            pass

    # Test Sheets
    sheets_ok = bool(
        os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or
        os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
    )

    uptime = int(time.time() - _start_time)

    return HealthResponse(
        status="healthy",
        serpapi=serpapi_ok,
        sheets=sheets_ok,
        version=__version__,
        uptime_seconds=uptime,
    )


def get_runtime_config() -> dict:
    """Get current runtime configuration (for use by other modules)."""
    return _runtime_config.copy()
