import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.models import Job, Video, Segment, Clip, Summary

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────

class SummaryOut(BaseModel):
    one_liner: str | None
    bullet_points: list[str] | None
    topic_tags: list[str] | None

    class Config:
        from_attributes = True


class ClipOut(BaseModel):
    id: str
    public_url: str | None
    duration: float | None
    summary: SummaryOut | None

    class Config:
        from_attributes = True


class SegmentOut(BaseModel):
    id: str
    index: int
    title: str | None
    start_time: float
    end_time: float
    transcript: str | None
    clip: ClipOut | None

    class Config:
        from_attributes = True


class ReelOut(BaseModel):
    job_id: str
    video_title: str | None
    video_duration: float | None
    segments: list[SegmentOut]

    class Config:
        from_attributes = True


class NoteSegment(BaseModel):
    index: int
    title: str | None
    start_time: float
    end_time: float
    one_liner: str | None
    bullet_points: list[str] | None


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=ReelOut)
def get_reel(job_id: str, db: Session = Depends(get_db)):
    """Get full reel data for a completed job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=202, detail=f"Job not ready. Status: {job.status}")

    video = (
        db.query(Video)
        .options(
            joinedload(Video.segments)
            .joinedload(Segment.clip)
            .joinedload(Clip.summary)
        )
        .filter(Video.job_id == job_id)
        .first()
    )

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return ReelOut(
        job_id=job_id,
        video_title=video.title,
        video_duration=video.duration,
        segments=video.segments,
    )


@router.get("/{job_id}/notes", response_model=list[NoteSegment])
def get_notes(job_id: str, db: Session = Depends(get_db)):
    """Get aggregated notes (all summaries) for a completed job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=202, detail="Job not ready")

    video = db.query(Video).filter(Video.job_id == job_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    segments = (
        db.query(Segment)
        .options(joinedload(Segment.clip).joinedload(Clip.summary))
        .filter(Segment.video_id == video.id)
        .order_by(Segment.index)
        .all()
    )

    notes = []
    for seg in segments:
        s = seg.clip.summary if seg.clip else None
        notes.append(NoteSegment(
            index=seg.index,
            title=seg.title,
            start_time=seg.start_time,
            end_time=seg.end_time,
            one_liner=s.one_liner if s else None,
            bullet_points=s.bullet_points if s else None,
        ))
    return notes
