import os
import shutil
import logging
import subprocess
import json
import torch
import yt_dlp
import whisper
import boto3

from botocore.config import Config
from groq import Groq
from app.core.config import settings
from app.repository.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

# Lazy loaded globals
_whisper_model = None
_groq_client = None
_s3_client = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        device = "cuda" if settings.WHISPER_DEVICE == "cuda" and torch.cuda.is_available() else "cpu"
        _whisper_model = whisper.load_model(settings.WHISPER_MODEL, device=device)
    return _whisper_model

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client

def _get_s3():
    global _s3_client
    if _s3_client is None and settings.R2_ACCOUNT_ID:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _s3_client

class VideoProcessor:
    def __init__(self, repository: ProjectRepository):
        self.repo = repository
        self.job_id = ""
        self.youtube_url = ""

    def process(self, job_id: str, youtube_url: str) -> None:
        self.job_id = job_id
        self.youtube_url = youtube_url
        
        try:
            self.repo.on_pipeline_start()

            # 1. Download
            title, duration, file_path = self._download_video()
            self.repo.on_download_complete(title, duration, self.youtube_url)

            # 2. Transcribe
            transcript_text, words, _ = self._transcribe_video(file_path)
            self.repo.on_transcription_complete(transcript_text)

            # 3. Segment
            segments = self._segment_transcript(words)
            # transform internal list of tuples into the expected raw dict for the repo event
            raw_segments = [
                {
                    "index": i,
                    "title": t,
                    "start_time": s,
                    "end_time": e,
                    "transcript": tr
                } for i, t, s, e, tr in segments
            ]
            self.repo.on_segmentation_complete(raw_segments)

            # 4, 5, 6. Extract, Summarize, Store
            n = len(segments)
            for seg_idx, seg_title, start_time, end_time, seg_transcript in segments:
                self.repo.on_clip_processing_start(seg_idx, n)

                clip_local = os.path.join(settings.TEMP_DIR, self.job_id, "clips", f"clip_{seg_idx:03d}.mp4")
                self._extract_clip(file_path, start_time, end_time, clip_local)

                ai_title, summary, bullets, tags = self._summarize_segment(seg_transcript, seg_idx)
                final_title = ai_title if ai_title and ai_title != f"Concept {seg_idx + 1}" else seg_title
                self.repo.on_segment_summarized(seg_idx, final_title, summary, bullets, tags)

                public_url = self._store_clip(clip_local, seg_idx)
                self.repo.on_clip_stored(seg_idx, clip_local, public_url, end_time - start_time)

            self.repo.on_pipeline_complete()
            self._cleanup_temp()
            logger.info(f"✅ Pipeline complete for job {self.job_id}")

        except Exception as e:
            logger.exception(f"Pipeline failed for job {self.job_id}: {e}")
            self.repo.on_pipeline_failed(str(e))
            self._cleanup_temp()

    def _download_video(self):
        output_dir = os.path.join(settings.TEMP_DIR, self.job_id)
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, "source.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        # Simplified for deep module (we omitted the retry browser loops for brevity here, but could keep them)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.youtube_url, download=True)
        
        file_path = None
        for fname in os.listdir(output_dir):
            if fname.startswith("source"):
                file_path = os.path.join(output_dir, fname)
                break

        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Downloaded file not found")

        return info.get("title", "Untitled"), float(info.get("duration", 0)), file_path

    def _transcribe_video(self, file_path: str):
        model = _get_whisper_model()
        result = model.transcribe(file_path, word_timestamps=True, verbose=False)
        words = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
        
        if not words:
            for seg in result.get("segments", []):
                words.append({"word": seg["text"], "start": seg["start"], "end": seg["end"]})
                
        duration = words[-1]["end"] if words else 0.0
        return result.get("text", "").strip(), words, duration

    def _segment_transcript(self, words: list[dict]):
        target = settings.SEGMENT_DURATION
        segments = []
        seg_start_idx = 0
        while seg_start_idx < len(words) and len(segments) < settings.MAX_SEGMENTS:
            start_word = words[seg_start_idx]
            target_end_time = start_word["start"] + target
            
            boundary_idx = seg_start_idx
            best_dist = float("inf")
            for i in range(seg_start_idx, len(words)):
                t = words[i]["end"]
                dist = abs(t - target_end_time)
                if dist < best_dist:
                    best_dist = dist
                    boundary_idx = i
                if t > target_end_time + 10:
                    break
                if words[i]["word"].strip().endswith((".", "?", "!")):
                    boundary_idx = i
                    break

            seg_words = words[seg_start_idx : boundary_idx + 1]
            if not seg_words:
                break
                
            seg_text = "".join(w["word"] for w in seg_words).strip()
            raw_words = seg_text.split()
            title = " ".join(raw_words[:8]) + ("..." if len(raw_words) > 8 else "")
            
            segments.append((len(segments), title, seg_words[0]["start"], seg_words[-1]["end"], seg_text))
            seg_start_idx = boundary_idx + 1
            
        return segments

    def _extract_clip(self, source_path: str, start_time: float, end_time: float, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-ss", f"{start_time:.3f}", "-to", f"{end_time:.3f}",
            "-i", source_path, "-c", "copy", "-avoid_negative_ts", "make_zero", output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            raise RuntimeError("FFmpeg output missing or too small")

    def _summarize_segment(self, transcript: str, index: int):
        client = _get_groq_client()
        prompt = f"Analyze this lecture transcript segment and respond ONLY with JSON.\nTranscript:\n{transcript[:3000]}\nRequired format: {{\"title\": \"...\", \"summary\": \"...\", \"bullets\": [\"...\"], \"tags\": [\"...\"]}}"
        try:
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            res = json.loads(content)
            return res.get("title", ""), res.get("summary", ""), res.get("bullets", []), res.get("tags", [])
        except Exception:
            return f"Concept {index + 1}", transcript[:120], [], []

    def _store_clip(self, local_path: str, segment_index: int):
        s3 = _get_s3()
        filename = f"{self.job_id}/clip_{segment_index:03d}.mp4"
        if s3 and settings.R2_PUBLIC_URL:
            r2_key = f"clips/{filename}"
            s3.upload_file(local_path, settings.R2_BUCKET_NAME, r2_key, ExtraArgs={"ContentType": "video/mp4"})
            return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
        else:
            dest_dir = os.path.join(settings.MEDIA_DIR, "clips", self.job_id)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"clip_{segment_index:03d}.mp4")
            shutil.copy2(local_path, dest_path)
            return f"{settings.BASE_URL}/media/clips/{self.job_id}/clip_{segment_index:03d}.mp4"

    def _cleanup_temp(self):
        temp_dir = os.path.join(settings.TEMP_DIR, self.job_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
