import logging

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.repository.sqlalchemy_repository import SQLAlchemyProjectRepository
from app.pipeline.processor import VideoProcessor

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="run_pipeline", max_retries=0)
def run_pipeline(self, job_id: str, youtube_url: str):
    """
    Celery task entrypoint.
    """
    db = SessionLocal()
    try:
        repo = SQLAlchemyProjectRepository(db, job_id)
        processor = VideoProcessor(repo)
        processor.process(job_id, youtube_url)
    finally:
        db.close()
