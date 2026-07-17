import os
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
# We will create this module in the next step
# from app.repository.sqlalchemy_repository import SQLAlchemyProjectRepository
from app.repository.project_repository import ProjectRepository

from app.pipeline.download import download_video
from app.pipeline.transcribe import transcribe_video
from app.pipeline.segment import segment_transcript
from app.pipeline.clip import extract_clip
from app.pipeline.summarize import summarize_segment
from app.pipeline.storage import store_clip, cleanup_temp
from app.core.config import settings

logger = logging.getLogger(__name__)

class ProcessingOrchestrator:
    def __init__(self, repository: ProjectRepository):
        self.repo = repository

    def run(self, job_id: str, youtube_url: str):
        try:
            # 1. Download
            dl = download_video(youtube_url, job_id)
            self.repo.on_download_complete(dl["title"], dl["duration"], youtube_url)

            # 2. Transcribe
            tr = transcribe_video(dl["file_path"])
            self.repo.on_transcription_complete(tr["text"])

            # 3. Segment
            raw_segments = segment_transcript(tr["words"], tr["duration"])
            self.repo.on_segmentation_complete(raw_segments)

            # 4, 5, 6. Clip, Summarize, Store
            n = len(raw_segments)
            for i, s in enumerate(raw_segments):
                self.repo.on_clip_processing_start(i, n)

                clip_local = os.path.join(settings.TEMP_DIR, job_id, "clips", f"clip_{i:03d}.mp4")
                extract_clip(dl["file_path"], s["start_time"], s["end_time"], clip_local)

                ai = summarize_segment(s["transcript"], i)
                ai_title = ai["title"] if ai["title"] and ai["title"] != f"Concept {i + 1}" else s["title"]
                self.repo.on_segment_summarized(i, ai_title, ai["summary"], ai["bullets"], ai["tags"])

                public_url = store_clip(clip_local, job_id, i)
                self.repo.on_clip_stored(i, clip_local, public_url, s["end_time"] - s["start_time"])

            self.repo.on_pipeline_complete()
            cleanup_temp(job_id)
            logger.info(f"✅ Pipeline complete for job {job_id} — {n} clips generated")
            
        except Exception as e:
            logger.exception(f"Pipeline failed for job {job_id}: {e}")
            self.repo.on_pipeline_failed(str(e))
            cleanup_temp(job_id)


from app.repository.sqlalchemy_repository import SQLAlchemyProjectRepository

@celery_app.task(bind=True, name="run_pipeline", max_retries=0)
def run_pipeline(self, job_id: str, youtube_url: str):
    """
    Celery task entrypoint.
    """
    db = SessionLocal()
    try:
        repo = SQLAlchemyProjectRepository(db, job_id)
        orchestrator = ProcessingOrchestrator(repo)
        orchestrator.run(job_id, youtube_url)
    finally:
        db.close()
