import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import Job, Video, Segment, Clip, Summary
from app.repository.sqlalchemy_repository import SQLAlchemyProjectRepository

@pytest.fixture
def db_session():
    # Use in-memory SQLite for testing the DB adapter
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    # Create a mock job to attach things to
    job = Job(id="job-123", status="pending", progress=0)
    db.add(job)
    db.commit()
    
    yield db
    db.close()


def test_sqlalchemy_repository_download_complete(db_session):
    repo = SQLAlchemyProjectRepository(db_session, "job-123")
    repo.on_download_complete("Title", 120.0, "http://url")
    
    video = db_session.query(Video).filter_by(job_id="job-123").first()
    assert video is not None
    assert video.title == "Title"
    assert video.duration == 120.0
    
    job = db_session.query(Job).filter_by(id="job-123").first()
    assert job.status == "processing"
    assert job.stage == "Downloading video..."


def test_sqlalchemy_repository_transcription_complete(db_session):
    repo = SQLAlchemyProjectRepository(db_session, "job-123")
    repo.on_download_complete("Title", 120.0, "http://url")
    repo.on_transcription_complete("Full transcript text")
    
    video = db_session.query(Video).filter_by(job_id="job-123").first()
    assert video.transcript == "Full transcript text"
    
    job = db_session.query(Job).filter_by(id="job-123").first()
    assert job.progress > 0
    assert job.stage == "Transcribing audio..."


def test_sqlalchemy_repository_segmentation_complete(db_session):
    repo = SQLAlchemyProjectRepository(db_session, "job-123")
    repo.on_download_complete("Title", 120.0, "http://url")
    
    raw_segments = [
        {"index": 0, "title": "C1", "start_time": 0.0, "end_time": 10.0, "transcript": "hello"}
    ]
    repo.on_segmentation_complete(raw_segments)
    
    video = db_session.query(Video).filter_by(job_id="job-123").first()
    assert len(video.segments) == 1
    assert video.segments[0].title == "C1"


def test_sqlalchemy_repository_full_flow(db_session):
    repo = SQLAlchemyProjectRepository(db_session, "job-123")
    repo.on_download_complete("Title", 120.0, "http://url")
    repo.on_segmentation_complete([
        {"index": 0, "title": "C1", "start_time": 0.0, "end_time": 10.0, "transcript": "hello"}
    ])
    
    repo.on_clip_processing_start(0, 1)
    repo.on_segment_summarized(0, "AI Title", "Sum", ["b1"], ["t1"])
    repo.on_clip_stored(0, "/tmp/clip.mp4", "http://pub", 10.0)
    
    video = db_session.query(Video).filter_by(job_id="job-123").first()
    seg = video.segments[0]
    
    assert seg.title == "AI Title"
    assert seg.clip is not None
    assert seg.clip.file_path == "/tmp/clip.mp4"
    assert seg.clip.summary.one_liner == "Sum"
    
    repo.on_pipeline_complete()
    job = db_session.query(Job).filter_by(id="job-123").first()
    assert job.status == "done"
    assert job.progress == 100
