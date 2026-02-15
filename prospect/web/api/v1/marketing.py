"""Anonymous marketing endpoints (no auth required)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from prospect.web.database import get_db, MarketingEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketing", tags=["marketing"])


class MarketingEventIn(BaseModel):
    event: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    anonymous_id: Optional[str] = None
    session_id: Optional[str] = None
    client_id: Optional[str] = None

    path: Optional[str] = None
    page_url: Optional[str] = None
    referrer: Optional[str] = None

    utm: Dict[str, Any] = Field(default_factory=dict)


@router.post("/events")
def ingest_event(payload: MarketingEventIn, request: Request, db: Session = Depends(get_db)):
    """Capture lightweight marketing events for funnel measurement."""

    # Map common UTM fields
    utm_source = payload.utm.get("utm_source")
    utm_campaign = payload.utm.get("utm_campaign")

    page_url = payload.page_url
    if not page_url and payload.path:
        page_url = str(payload.path)

    ev = MarketingEvent(
        event_name=payload.event,
        event_type="marketing",
        source=utm_source,
        campaign=utm_campaign,
        anonymous_id=payload.anonymous_id,
        client_id=payload.client_id or payload.session_id,
        page_url=page_url,
        occurred_at=datetime.utcnow(),
        event_metadata={
            "properties": payload.properties,
            "utm": payload.utm,
            "path": payload.path,
            "referrer": payload.referrer,
            "session_id": payload.session_id,
            "user_agent": request.headers.get("user-agent"),
        },
    )

    try:
        db.add(ev)
        db.commit()
    except Exception as e:
        # Keep the endpoint non-blocking for the caller.
        logger.warning(f"Failed to persist marketing event: {e}")
        db.rollback()

    return {"ok": True}
