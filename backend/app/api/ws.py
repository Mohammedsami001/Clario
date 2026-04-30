import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import Job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/jobs/{job_id}")
async def job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint — streams live job progress to the frontend.
    Sends a JSON message every second until the job is done or failed.
    """
    await websocket.accept()
    db: Session = SessionLocal()

    try:
        while True:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                await websocket.send_text(json.dumps({"error": "Job not found"}))
                break

            payload = {
                "job_id": job_id,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "error_msg": job.error_msg,
            }
            await websocket.send_text(json.dumps(payload))

            if job.status in ("done", "failed"):
                break

            # Refresh session for next poll
            db.expire_all()
            await asyncio.sleep(1.5)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    finally:
        db.close()
