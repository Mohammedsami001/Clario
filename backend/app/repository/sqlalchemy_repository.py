import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import Job, Video, Segment, Clip, Summary
from app.repository.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

class SQLAlchemyProjectRepository(ProjectRepository):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        
        # Load the job to ensure it exists
        self.job = self.db.query(Job).filter_by(id=job_id).first()
        if not self.job:
            raise ValueError(f"Job {job_id} not found")
        self.video = self.db.query(Video).filter_by(job_id=job_id).first()

    def _update_job(self, status: str, stage: str, progress: int) -> None:
        self.job.status = status
        self.job.stage = stage
        self.job.progress = progress
        self.job.updated_at = datetime.utcnow()
        self.db.commit()
        logger.info(f"[Job {self.job_id}] {stage} — {progress}%")

    def on_download_complete(self, title: str, duration: float, source_url: str) -> None:
        self._update_job("processing", "Downloading video...", 5)
        
        self.video = Video(
            job_id=self.job_id,
            title=title,
            duration=duration,
            source_url=source_url,
        )
        self.db.add(self.video)
        self.db.commit()
        self.db.refresh(self.video)

    def on_transcription_complete(self, transcript_text: str) -> None:
        self._update_job("processing", "Transcribing audio...", 20)
        self.video.transcript = transcript_text
        self.db.commit()

    def on_segmentation_complete(self, raw_segments: List[Dict[str, Any]]) -> None:
        self._update_job("processing", "Segmenting into concepts...", 40)
        
        for s in raw_segments:
            seg = Segment(
                video_id=self.video.id,
                index=s["index"],
                title=s["title"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                transcript=s["transcript"],
            )
            self.db.add(seg)
        self.db.commit()

    def on_clip_processing_start(self, segment_index: int, total_segments: int) -> None:
        base_progress = 50 + int((segment_index / total_segments) * 45)
        self._update_job("processing", f"Processing clip {segment_index + 1}/{total_segments}...", base_progress)

    def on_segment_summarized(self, segment_index: int, ai_title: str, summary: str, bullets: List[str], tags: List[str]) -> None:
        # Load the segment
        seg = self.db.query(Segment).filter_by(video_id=self.video.id, index=segment_index).first()
        if seg:
            seg.title = ai_title
            self.db.commit()
            
        # We temporarily store summary data on the instance so we can attach it when the clip is stored
        # Or we can insert it now if we attach it to the segment... but our schema attaches Summary to Clip.
        if not hasattr(self, "_pending_summaries"):
            self._pending_summaries = {}
        self._pending_summaries[segment_index] = {
            "one_liner": summary,
            "bullet_points": bullets,
            "topic_tags": tags
        }

    def on_clip_stored(self, segment_index: int, local_path: str, public_url: str, duration: float) -> None:
        seg = self.db.query(Segment).filter_by(video_id=self.video.id, index=segment_index).first()
        if not seg:
            return
            
        clip = Clip(
            segment_id=seg.id,
            file_path=local_path,
            public_url=public_url,
            duration=duration,
        )
        self.db.add(clip)
        self.db.commit()
        self.db.refresh(clip)
        
        pending_ai = getattr(self, "_pending_summaries", {}).get(segment_index)
        if pending_ai:
            summary = Summary(
                clip_id=clip.id,
                one_liner=pending_ai["one_liner"],
                bullet_points=pending_ai["bullet_points"],
                topic_tags=pending_ai["topic_tags"],
            )
            self.db.add(summary)
            self.db.commit()

    def on_pipeline_complete(self) -> None:
        self._update_job("done", "Complete!", 100)

    def on_pipeline_failed(self, error_msg: str) -> None:
        self.job.status = "failed"
        self.job.stage = "Failed"
        self.job.error_msg = error_msg
        self.job.updated_at = datetime.utcnow()
        self.db.commit()
