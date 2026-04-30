import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    status = Column(String, default="pending")   # pending|processing|done|failed
    stage = Column(String, nullable=True)        # human-readable current stage label
    progress = Column(Integer, default=0)        # 0–100
    error_msg = Column(Text, nullable=True)
    youtube_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    video = relationship("Video", back_populates="job", uselist=False)


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), unique=True)
    title = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    source_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="video")
    segments = relationship("Segment", back_populates="video", order_by="Segment.index")


class Segment(Base):
    __tablename__ = "segments"

    id = Column(String, primary_key=True, default=_uuid)
    video_id = Column(String, ForeignKey("videos.id"))
    index = Column(Integer)
    title = Column(String, nullable=True)
    start_time = Column(Float)
    end_time = Column(Float)
    transcript = Column(Text, nullable=True)

    video = relationship("Video", back_populates="segments")
    clip = relationship("Clip", back_populates="segment", uselist=False)


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=_uuid)
    segment_id = Column(String, ForeignKey("segments.id"), unique=True)
    file_path = Column(String, nullable=True)    # local path (dev)
    public_url = Column(String, nullable=True)   # R2 URL (prod)
    duration = Column(Float, nullable=True)

    segment = relationship("Segment", back_populates="clip")
    summary = relationship("Summary", back_populates="clip", uselist=False)


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(String, primary_key=True, default=_uuid)
    clip_id = Column(String, ForeignKey("clips.id"), unique=True)
    one_liner = Column(Text, nullable=True)
    bullet_points = Column(JSON, nullable=True)  # ["point 1", "point 2", ...]
    topic_tags = Column(JSON, nullable=True)     # ["entropy", "thermodynamics"]

    clip = relationship("Clip", back_populates="summary")
