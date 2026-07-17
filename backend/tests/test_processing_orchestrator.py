from typing import List, Dict, Any, Tuple
from unittest.mock import patch

from app.repository.project_repository import ProjectRepository
# We will create this class in the next step to pass the test
from app.tasks.process_video import ProcessingOrchestrator

class InMemoryProjectRepository(ProjectRepository):
    def __init__(self):
        self.events: List[Tuple[str, Any]] = []

    def on_download_complete(self, title: str, duration: float, source_url: str) -> None:
        self.events.append(("download_complete", (title, duration, source_url)))

    def on_transcription_complete(self, transcript_text: str) -> None:
        self.events.append(("transcription_complete", (transcript_text,)))

    def on_segmentation_complete(self, raw_segments: List[Dict[str, Any]]) -> None:
        self.events.append(("segmentation_complete", (raw_segments,)))

    def on_clip_processing_start(self, segment_index: int, total_segments: int) -> None:
        self.events.append(("clip_processing_start", (segment_index, total_segments)))

    def on_segment_summarized(self, segment_index: int, ai_title: str, summary: str, bullets: List[str], tags: List[str]) -> None:
        self.events.append(("segment_summarized", (segment_index, ai_title, summary, bullets, tags)))

    def on_clip_stored(self, segment_index: int, local_path: str, public_url: str, duration: float) -> None:
        self.events.append(("clip_stored", (segment_index, local_path, public_url, duration)))

    def on_pipeline_complete(self) -> None:
        self.events.append(("pipeline_complete", ()))

    def on_pipeline_failed(self, error_msg: str) -> None:
        self.events.append(("pipeline_failed", (error_msg,)))


@patch("app.tasks.process_video.download_video")
@patch("app.tasks.process_video.transcribe_video")
@patch("app.tasks.process_video.segment_transcript")
@patch("app.tasks.process_video.extract_clip")
@patch("app.tasks.process_video.summarize_segment")
@patch("app.tasks.process_video.store_clip")
@patch("app.tasks.process_video.cleanup_temp")
def test_processing_orchestrator_success(
    mock_cleanup, mock_store, mock_summarize, mock_extract, mock_segment, mock_transcribe, mock_download
):
    # Setup mocks
    mock_download.return_value = {"title": "Test Video", "duration": 120.0, "file_path": "/tmp/vid.mp4"}
    mock_transcribe.return_value = {"text": "hello world", "words": [], "duration": 120.0}
    mock_segment.return_value = [
        {"index": 0, "title": "Concept 1", "start_time": 0.0, "end_time": 60.0, "transcript": "hello"},
        {"index": 1, "title": "Concept 2", "start_time": 60.0, "end_time": 120.0, "transcript": "world"},
    ]
    mock_summarize.return_value = {
        "title": "AI Title",
        "summary": "AI Summary",
        "bullets": ["Point"],
        "tags": ["tag1"]
    }
    mock_store.return_value = "https://cdn.com/clip.mp4"

    # Run orchestrator
    repo = InMemoryProjectRepository()
    orchestrator = ProcessingOrchestrator(repo)
    orchestrator.run("job-123", "https://youtube.com/watch?v=123")

    # Assert correct domain events were emitted in order
    event_names = [e[0] for e in repo.events]
    assert event_names == [
        "download_complete",
        "transcription_complete",
        "segmentation_complete",
        "clip_processing_start", # clip 0
        "segment_summarized",
        "clip_stored",
        "clip_processing_start", # clip 1
        "segment_summarized",
        "clip_stored",
        "pipeline_complete"
    ]

    # Verify download event data
    assert repo.events[0][1] == ("Test Video", 120.0, "https://youtube.com/watch?v=123")
    
    # Verify cleanup was called
    mock_cleanup.assert_called_once_with("job-123")


@patch("app.tasks.process_video.download_video")
@patch("app.tasks.process_video.cleanup_temp")
def test_processing_orchestrator_failure(mock_cleanup, mock_download):
    mock_download.side_effect = Exception("Download failed")
    
    repo = InMemoryProjectRepository()
    orchestrator = ProcessingOrchestrator(repo)
    orchestrator.run("job-123", "https://youtube.com/watch?v=123")

    # Verify failure event
    assert len(repo.events) == 1
    assert repo.events[0][0] == "pipeline_failed"
    assert "Download failed" in repo.events[0][1][0]
    
    mock_cleanup.assert_called_once_with("job-123")
