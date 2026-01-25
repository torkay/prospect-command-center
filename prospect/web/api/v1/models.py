"""Pydantic models for API v1."""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class SearchDepth(str, Enum):
    """Search depth tier."""
    quick = "quick"
    standard = "standard"
    deep = "deep"
    exhaustive = "exhaustive"


class Filters(BaseModel):
    """Search filters."""
    min_fit: int = 0
    min_opportunity: int = 0
    min_priority: float = 0
    require_phone: bool = False
    require_email: bool = False
    exclude_domains: List[str] = Field(default_factory=list)


class ScoringConfig(BaseModel):
    """Scoring configuration."""
    fit_weight: float = 0.4
    opportunity_weight: float = 0.6


class SearchRequest(BaseModel):
    """Search request payload."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "business_type": "buyer's agent",
                "location": "Brisbane, QLD",
                "limit": 20,
                "depth": "standard",
                "skip_enrichment": False,
                "parallel": 3,
                "filters": {
                    "min_priority": 40,
                    "require_phone": True
                }
            }
        }
    )

    business_type: str
    location: str
    limit: int = Field(default=20, le=200, ge=1)
    depth: SearchDepth = SearchDepth.standard
    skip_enrichment: bool = False
    parallel: int = Field(default=3, le=10, ge=1)
    filters: Filters = Field(default_factory=Filters)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


class JobResponse(BaseModel):
    """Job creation response."""
    id: str
    status: str
    message: str
    depth: Optional[str] = None
    searches_remaining: Optional[int] = None


class SearchEstimate(BaseModel):
    """Search estimate response."""
    queries: List[str]
    locations: List[str]
    total_api_calls: int
    estimated_cost_cents: int
    estimated_prospects: str
    warning: Optional[str] = None


class SearchConfigResponse(BaseModel):
    """Search configuration info."""
    name: str
    description: str
    estimated_cost_cents: int
    max_api_calls: int
    estimated_prospects: str
