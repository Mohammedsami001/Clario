import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Job, Video
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    youtube_url: str


class JobResponse(BaseModel):
    id: str
    status: str
    stage: str | None
    progress: int
    error_msg: str | None
    youtube_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("", response_model=JobResponse, status_code=201)
def create_job(payload: CreateJobRequest, db: Session = Depends(get_db)):
    """Submit a YouTube URL — creates a job and enqueues the pipeline."""
    job = Job(youtube_url=payload.youtube_url, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Fire Celery task asynchronously
    from app.tasks.process_video import run_pipeline
    run_pipeline.delay(job.id, payload.youtube_url)

    logger.info(f"Job created: {job.id} for URL: {payload.youtube_url}")
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Poll job status and progress."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """List all jobs (most recent first)."""
    return db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
