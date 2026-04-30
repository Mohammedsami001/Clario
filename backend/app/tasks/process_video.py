import os
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import Job, Video, Segment, Clip, Summary

from app.pipeline.download import download_video
from app.pipeline.transcribe import transcribe_video
from app.pipeline.segment import segment_transcript
from app.pipeline.clip import extract_clip
from app.pipeline.summarize import summarize_segment
from app.pipeline.storage import store_clip, cleanup_temp
from app.core.config import settings

logger = logging.getLogger(__name__)


def _update_job(db, job: Job, status: str, stage: str, progress: int):
    """Helper to update job state in DB."""
    job.status = status
    job.stage = stage
    job.progress = progress
    job.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"[Job {job.id}] {stage} — {progress}%")


@celery_app.task(bind=True, name="run_pipeline", max_retries=0)
def run_pipeline(self, job_id: str, youtube_url: str):
    """
    Full Clario pipeline:
      1. Download video (yt-dlp)
      2. Transcribe (faster-whisper + CUDA)
      3. Segment transcript (time-based)
      4. Extract clips (FFmpeg)
      5. Summarize each clip (Groq)
      6. Store clips (local or R2)
      7. Mark job done
    """
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        logger.error(f"Job {job_id} not found")
        db.close()
        return

    try:
        # ── Stage 1: Download ─────────────────────────────────────────────
        _update_job(db, job, "processing", "Downloading video...", 5)
        dl = download_video(youtube_url, job_id)

        video = Video(
            job_id=job_id,
            title=dl["title"],
            duration=dl["duration"],
            source_url=youtube_url,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # ── Stage 2: Transcribe ───────────────────────────────────────────
        _update_job(db, job, "processing", "Transcribing audio...", 20)
        tr = transcribe_video(dl["file_path"])

        video.transcript = tr["text"]
        db.commit()

        # ── Stage 3: Segment ──────────────────────────────────────────────
        _update_job(db, job, "processing", "Segmenting into concepts...", 40)
        raw_segments = segment_transcript(tr["words"], tr["duration"])

        seg_models = []
        for s in raw_segments:
            seg = Segment(
                video_id=video.id,
                index=s["index"],
                title=s["title"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                transcript=s["transcript"],
            )
            db.add(seg)
            seg_models.append((seg, s))
        db.commit()
        for seg, _ in seg_models:
            db.refresh(seg)

        # ── Stages 4 + 5 + 6: Clip → Summarize → Store (per segment) ─────
        n = len(seg_models)
        for i, (seg, s) in enumerate(seg_models):
            base_progress = 50 + int((i / n) * 45)
            _update_job(db, job, "processing", f"Processing clip {i + 1}/{n}...", base_progress)

            # 4. Extract clip
            clip_local = os.path.join(settings.TEMP_DIR, job_id, "clips", f"clip_{i:03d}.mp4")
            extract_clip(dl["file_path"], s["start_time"], s["end_time"], clip_local)

            # 5. Summarize
            ai = summarize_segment(s["transcript"], i)

            # Update segment title from AI if it returned one
            if ai["title"] and ai["title"] != f"Concept {i + 1}":
                seg.title = ai["title"]
                db.commit()

            # 6. Store
            public_url = store_clip(clip_local, job_id, i)

            clip = Clip(
                segment_id=seg.id,
                file_path=clip_local,
                public_url=public_url,
                duration=s["end_time"] - s["start_time"],
            )
            db.add(clip)
            db.commit()
            db.refresh(clip)

            summary = Summary(
                clip_id=clip.id,
                one_liner=ai["summary"],
                bullet_points=ai["bullets"],
                topic_tags=ai["tags"],
            )
            db.add(summary)
            db.commit()

        # ── Stage 7: Done ─────────────────────────────────────────────────
        _update_job(db, job, "done", "Complete!", 100)
        cleanup_temp(job_id)
        logger.info(f"✅ Pipeline complete for job {job_id} — {n} clips generated")

    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}: {e}")
        job.status = "failed"
        job.stage = "Failed"
        job.error_msg = str(e)
        job.updated_at = datetime.utcnow()
        db.commit()
        cleanup_temp(job_id)
    finally:
        db.close()
