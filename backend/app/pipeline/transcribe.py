import logging

from faster_whisper import WhisperModel

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    """Lazy-load and cache the Whisper model (loads once per worker process)."""
    global _model
    if _model is None:
        logger.info(
            f"Loading Whisper model '{settings.WHISPER_MODEL}' "
            f"on {settings.WHISPER_DEVICE} ({settings.WHISPER_COMPUTE_TYPE})"
        )
        _model = WhisperModel(
            settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded ✅")
    return _model


def transcribe_video(file_path: str) -> dict:
    """
    Transcribe a video file using faster-whisper.
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

    segments_iter, info = model.transcribe(
        file_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    words = []
    text_parts = []

    for seg in segments_iter:
        text_parts.append(seg.text.strip())
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": w.start, "end": w.end})
        else:
            # Fallback: use segment-level timestamps if word timestamps unavailable
            words.append({"word": seg.text, "start": seg.start, "end": seg.end})

    full_text = " ".join(text_parts)
    logger.info(f"Transcription done — {len(words)} words, language: {info.language}")

    return {
        "text": full_text,
        "words": words,
        "language": info.language,
        "duration": info.duration,
    }
