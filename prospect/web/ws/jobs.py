"""WebSocket endpoint for real-time job updates."""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from prospect.web.state import job_manager, JobStatus

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket for real-time job progress.

    Messages:
        - {"type": "progress", "status": "searching", "progress": 5, "total": 20, "message": "..."}
        - {"type": "complete", "count": 18, "duration_ms": 12345}
        - {"type": "error", "message": "..."}

    Example (JavaScript):
        const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);
        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'progress') {
                updateProgress(data.progress, data.total);
            } else if (data.type === 'complete') {
                fetchResults(jobId);
            }
        };
    """
    await websocket.accept()

    try:
        last_progress = -1
        last_status = None

        while True:
            job = await job_manager.get_job(job_id)

            if not job:
                await websocket.send_json({
                    "type": "error",
                    "message": "Job not found"
                })
                break

            # Send progress update if changed
            if job.progress != last_progress or job.status != last_status:
                last_progress = job.progress
                last_status = job.status

                await websocket.send_json({
                    "type": "progress",
                    "status": job.status.value,
                    "progress": job.progress,
                    "total": job.progress_total,
                    "message": job.progress_message or "Processing...",
                })

            # Check for completion
            if job.status == JobStatus.COMPLETE:
                await websocket.send_json({
                    "type": "complete",
                    "count": len(job.results) if job.results else 0,
                    "duration_ms": job.duration_ms,
                })
                break

            elif job.status == JobStatus.ERROR:
                await websocket.send_json({
                    "type": "error",
                    "message": job.error or "Unknown error"
                })
                break

            # Poll interval
            await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
