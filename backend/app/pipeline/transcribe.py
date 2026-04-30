import logging

import torch
import whisper

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load and cache the Whisper model (loaded once per worker process)."""
    global _model
    if _model is None:
        device = "cuda" if settings.WHISPER_DEVICE == "cuda" and torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Whisper model '{settings.WHISPER_MODEL}' on {device}")
        _model = whisper.load_model(settings.WHISPER_MODEL, device=device)
        logger.info(f"Whisper model loaded ✅  (device: {device})")
    return _model


def transcribe_video(file_path: str) -> dict:
    """
    Transcribe a video/audio file using openai-whisper.
    Returns:
        {
            "text": str,           # full transcript
            "words": [{"word", "start", "end"}, ...],
            "language": str,
            "duration": float,
        }
    """
    model = _get_model()
    logger.info(f"Transcribing: {file_path}")

    result = model.transcribe(
        file_path,
        word_timestamps=True,
        verbose=False,
        fp16=torch.cuda.is_available(),  # fp16 only on GPU
    )

    # Flatten word-level timestamps from all segments
    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"],
                "start": w["start"],
                "end": w["end"],
            })

    # Fallback: if word timestamps empty, use segment-level
    if not words:
        logger.warning("Word timestamps unavailable — falling back to segment-level")
        for seg in result.get("segments", []):
            words.append({
                "word": seg["text"],
                "start": seg["start"],
                "end": seg["end"],
            })

    # Calculate duration from last word end
    duration = words[-1]["end"] if words else 0.0

    logger.info(f"Transcription done — {len(words)} words, language: {result.get('language')}")

    return {
        "text": result.get("text", "").strip(),
        "words": words,
        "language": result.get("language", "en"),
        "duration": duration,
    }
