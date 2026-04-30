import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def extract_clip(source_path: str, start_time: float, end_time: float, output_path: str) -> str:
    """
    Extract a clip from source_path using FFmpeg (stream copy — no re-encode).
    Returns the output_path on success.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                          # overwrite output
        "-ss", f"{start_time:.3f}",    # seek before input (fast)
        "-to", f"{end_time:.3f}",
        "-i", source_path,
        "-c", "copy",                  # no re-encode = fast
        "-avoid_negative_ts", "make_zero",
        output_path,
    ]

    logger.info(f"FFmpeg: {start_time:.1f}s → {end_time:.1f}s → {output_path}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        logger.error(f"FFmpeg stderr: {result.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg failed (code {result.returncode}): {result.stderr[-300:]}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
        raise RuntimeError(f"FFmpeg output missing or too small: {output_path}")

    return output_path
