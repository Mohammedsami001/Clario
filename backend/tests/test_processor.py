from typing import List, Dict, Any, Tuple
from unittest.mock import patch, MagicMock

from app.repository.project_repository import ProjectRepository
from app.pipeline.processor import VideoProcessor

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


@patch("app.pipeline.processor.yt_dlp.YoutubeDL")
@patch("app.pipeline.processor.whisper.load_model")
@patch("app.pipeline.processor.Groq")
@patch("app.pipeline.processor.subprocess.run")
@patch("app.pipeline.processor.shutil.copy2")
@patch("app.pipeline.processor.os.listdir")
@patch("app.pipeline.processor.os.path.exists")
@patch("app.pipeline.processor.os.path.getsize")
@patch("app.pipeline.processor.os.makedirs")
@patch("app.pipeline.processor.shutil.rmtree")
def test_video_processor_success(
    mock_rmtree, mock_makedirs, mock_getsize, mock_exists, mock_listdir, mock_copy2,
    mock_subprocess, mock_groq, mock_whisper_load, mock_ytdl
):
    # Mock yt-dlp
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {
        "title": "Test Video",
        "duration": 120.0
    }
    mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
    mock_listdir.return_value = ["source.mp4"]
    mock_exists.return_value = True
    mock_getsize.return_value = 2048 # large enough clip

    # Mock whisper
    mock_whisper_model = MagicMock()
    mock_whisper_model.transcribe.return_value = {
        "text": "hello world",
        "segments": [
            {
                "words": [
                    {"word": "hello", "start": 0.0, "end": 1.0},
                    {"word": "world.", "start": 1.0, "end": 2.0}
                ]
            }
        ]
    }
    mock_whisper_load.return_value = mock_whisper_model

    # Mock FFmpeg subprocess
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result

    # Mock Groq
    mock_groq_instance = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"title": "AI Title", "summary": "AI Summary", "bullets": ["b1"], "tags": ["t1"]}'
    mock_groq_instance.chat.completions.create.return_value.choices = [mock_choice]
    mock_groq.return_value = mock_groq_instance

    # Run processor
    repo = InMemoryProjectRepository()
    processor = VideoProcessor(repo)
    processor.process("job-123", "https://youtube.com/watch?v=123")

    # Verify domain events
    event_names = [e[0] for e in repo.events]
    assert "download_complete" in event_names
    assert "transcription_complete" in event_names
    assert "segmentation_complete" in event_names
    assert "clip_processing_start" in event_names
    assert "segment_summarized" in event_names
    assert "clip_stored" in event_names
    assert "pipeline_complete" in event_names


@patch("app.pipeline.processor.yt_dlp.YoutubeDL")
@patch("app.pipeline.processor.os.makedirs")
@patch("app.pipeline.processor.shutil.rmtree")
def test_video_processor_failure(mock_rmtree, mock_makedirs, mock_ytdl):
    mock_ytdl.side_effect = Exception("Download Failed")
    
    repo = InMemoryProjectRepository()
    processor = VideoProcessor(repo)
    processor.process("job-123", "https://youtube.com/watch?v=123")
    
    assert len(repo.events) == 1
    assert repo.events[0][0] == "pipeline_failed"
    assert "Download Failed" in repo.events[0][1][0]
