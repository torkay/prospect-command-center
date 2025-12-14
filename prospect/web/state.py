"""In-memory state management for search jobs."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class JobStatus(Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    ENRICHING = "enriching"
    SCORING = "scoring"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class SearchJob:
    """Represents a search job and its state."""
    id: str
    business_type: str
    location: str
    limit: int
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    progress_total: int = 0
    progress_message: str = ""
    results: list = field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    config: Optional[dict] = None  # Store search configuration
    duration_ms: Optional[int] = None  # Duration in milliseconds


class JobManager:
    """Manages search jobs in memory."""

    def __init__(self):
        self._jobs: dict[str, SearchJob] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self,
        business_type: str,
        location: str,
        limit: int,
        config: Optional[dict] = None,
    ) -> SearchJob:
        """Create a new search job."""
        job_id = str(uuid.uuid4())[:8]
        job = SearchJob(
            id=job_id,
            business_type=business_type,
            location=location,
            limit=limit,
            config=config,
        )

        async with self._lock:
            self._jobs[job_id] = job

        return job

    async def get_job(self, job_id: str) -> Optional[SearchJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def list_jobs(
        self,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> List[SearchJob]:
        """List jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())

        # Filter by status if provided
        if status:
            try:
                status_enum = JobStatus(status)
                jobs = [j for j in jobs if j.status == status_enum]
            except ValueError:
                pass

        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        progress_total: Optional[int] = None,
        progress_message: Optional[str] = None,
        results: Optional[list] = None,
        error: Optional[str] = None,
    ) -> Optional[SearchJob]:
        """Update a job's state."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        async with self._lock:
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if progress_total is not None:
                job.progress_total = progress_total
            if progress_message is not None:
                job.progress_message = progress_message
            if results is not None:
                job.results = results
            if error is not None:
                job.error = error

            if status == JobStatus.COMPLETE or status == JobStatus.ERROR:
                job.completed_at = datetime.now()
                # Calculate duration
                if job.created_at:
                    delta = job.completed_at - job.created_at
                    job.duration_ms = int(delta.total_seconds() * 1000)

        return job

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID."""
        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    async def cleanup_old_jobs(self, max_age_minutes: int = 60):
        """Remove jobs older than max_age_minutes."""
        now = datetime.now()
        async with self._lock:
            old_jobs = [
                job_id for job_id, job in self._jobs.items()
                if (now - job.created_at).total_seconds() > max_age_minutes * 60
            ]
            for job_id in old_jobs:
                del self._jobs[job_id]


# Global job manager
job_manager = JobManager()
