"""Pydantic models for API v1."""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


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
    limit: int = Field(default=20, le=100, ge=1)
    skip_enrichment: bool = False
    parallel: int = Field(default=3, le=10, ge=1)
    filters: Filters = Field(default_factory=Filters)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


class JobResponse(BaseModel):
    """Job creation response."""
    id: str
    status: str
    message: str
