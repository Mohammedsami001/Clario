import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def segment_transcript(words: list[dict], total_duration: float) -> list[dict]:
    """
    Split transcript words into time-based segments of ~SEGMENT_DURATION seconds.
    Attempts to break at sentence boundaries (., ?, !) within a ±10s window.

    Returns list of:
        {index, title, start_time, end_time, transcript}
    """
    target = settings.SEGMENT_DURATION
    max_segs = settings.MAX_SEGMENTS

    if not words:
        logger.warning("No words to segment")
        return []

    segments = []
    seg_start_idx = 0

    while seg_start_idx < len(words) and len(segments) < max_segs:
        start_word = words[seg_start_idx]
        target_end_time = start_word["start"] + target

        # Find a good sentence boundary near target_end_time
        boundary_idx = _find_boundary(words, seg_start_idx, target_end_time)

        seg_words = words[seg_start_idx : boundary_idx + 1]
        if not seg_words:
            break

        seg_text = "".join(w["word"] for w in seg_words).strip()
        raw_words = seg_text.split()
        title = " ".join(raw_words[:8]) + ("..." if len(raw_words) > 8 else "")

        segments.append({
            "index": len(segments),
            "title": title,
            "start_time": seg_words[0]["start"],
            "end_time": seg_words[-1]["end"],
            "transcript": seg_text,
        })

        seg_start_idx = boundary_idx + 1

    logger.info(f"Segmented into {len(segments)} segments")
    return segments


def _find_boundary(words: list[dict], from_idx: int, target_time: float, window: float = 10.0) -> int:
    """
    Return the index of the best sentence-ending word near target_time.
    Falls back to the word closest to target_time if no sentence boundary found.
    """
    best_sentence_idx = None
    best_sentence_dist = float("inf")
    closest_idx = from_idx
    closest_dist = float("inf")

    for i in range(from_idx, len(words)):
        t = words[i]["end"]
        dist = abs(t - target_time)

        # Track closest word overall
        if dist < closest_dist:
            closest_dist = dist
            closest_idx = i

        # Stop searching far past the window
        if t > target_time + window + 5:
            break

        # Check for sentence boundary
        word_text = words[i]["word"].strip()
        if word_text.endswith((".", "?", "!", ".\n")):
            if dist < best_sentence_dist:
                best_sentence_dist = dist
                best_sentence_idx = i

    return best_sentence_idx if best_sentence_idx is not None else closest_idx
