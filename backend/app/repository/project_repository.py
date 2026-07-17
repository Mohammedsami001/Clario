from typing import Protocol, List, Dict, Any

class ProjectRepository(Protocol):
    """
    Interface for persisting the state of a Video Processing Project.
    The implementations are responsible for managing UI progress updates
    based on the domain events emitted here.
    """

    def on_download_complete(self, title: str, duration: float, source_url: str) -> None:
        """Called when the video is downloaded."""
        ...

    def on_transcription_complete(self, transcript_text: str) -> None:
        """Called when the audio transcription is finished."""
        ...

    def on_segmentation_complete(self, raw_segments: List[Dict[str, Any]]) -> None:
        """
        Called when the transcript is split into semantic segments.
        raw_segments should be a list of dicts with: index, title, start_time, end_time, transcript
        """
        ...
        
    def on_clip_processing_start(self, segment_index: int, total_segments: int) -> None:
        """Called before a specific clip begins extraction/summarization."""
        ...

    def on_segment_summarized(self, segment_index: int, ai_title: str, summary: str, bullets: List[str], tags: List[str]) -> None:
        """Called when Groq has summarized the segment."""
        ...

    def on_clip_stored(self, segment_index: int, local_path: str, public_url: str, duration: float) -> None:
        """Called when the clip MP4 is extracted and stored."""
        ...

    def on_pipeline_complete(self) -> None:
        """Called when all clips are successfully processed."""
        ...

    def on_pipeline_failed(self, error_msg: str) -> None:
        """Called if the pipeline encounters an unrecoverable error."""
        ...
