import os
import logging

import yt_dlp

from app.core.config import settings

logger = logging.getLogger(__name__)


def download_video(youtube_url: str, job_id: str) -> dict:
    """
    Download a YouTube video to temp/{job_id}/source.mp4.
    Returns: {"title": str, "duration": float, "file_path": str}
    """
    output_dir = os.path.join(settings.TEMP_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "source.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,

        # ── Anti-403 fixes ────────────────────────────────────────
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_retries": 3,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
    }

    # Use browser cookies if available (helps bypass bot detection)
    # Try Chrome first, then Edge, then Firefox
    for browser in ["chrome", "edge", "firefox"]:
        try:
            test_opts = {**ydl_opts, "cookiesfrombrowser": (browser,)}
            with yt_dlp.YoutubeDL(test_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
            logger.info(f"Downloaded using {browser} cookies: {info.get('title')}")
            return _find_result(info, output_dir)
        except Exception as e:
            logger.warning(f"Failed with {browser} cookies: {e}")
            continue

    # Fallback: no cookies
    logger.info("Trying download without browser cookies...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)

    return _find_result(info, output_dir)


def _find_result(info: dict, output_dir: str) -> dict:
    """Locate the downloaded file and return metadata."""
    file_path = None
    for fname in os.listdir(output_dir):
        if fname.startswith("source"):
            file_path = os.path.join(output_dir, fname)
            break

    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"Downloaded file not found in {output_dir}")

    logger.info(f"Downloaded: {info.get('title')} → {file_path}")

    return {
        "title": info.get("title", "Untitled"),
        "duration": float(info.get("duration", 0)),
        "file_path": file_path,
    }
