<div align="center">

# ⚡ Clario

### Turn any YouTube lecture into a scrollable study reel.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Whisper](https://img.shields.io/badge/OpenAI_Whisper-Local_GPU-412991?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br />

**Clario** takes a 2-hour YouTube lecture, transcribes it with AI, breaks it into bite-sized concepts, generates video clips, and presents them in a TikTok-style vertical reel — each clip paired with an AI-generated summary and bullet points.

No more scrubbing through boring lectures. Just scroll, learn, repeat.

<br />

[🚀 Quick Start](#-quick-start) · [🏗️ Architecture](#️-system-architecture) · [📡 API Docs](#-api-endpoints) · [🧠 Pipeline](#-the-ai-pipeline) · [🛠️ Tech Stack](#️-tech-stack)

</div>

---

## 🎯 The Problem

> 300M+ students worldwide watch YouTube lectures. The average lecture is 90 minutes. The average attention span is 8 seconds. **The math doesn't work.**

Students waste hours scrubbing through long videos, re-watching sections, and taking notes manually. Clario fixes this by converting any lecture into structured, scrollable, summarized micro-content — automatically.

---

## ✨ What Clario Does

```
  YouTube URL
       │
       ▼
  ┌─────────────┐
  │  📥 Download │  yt-dlp (720p, anti-bot, cookie support)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  🎤 Transcribe │  OpenAI Whisper (local GPU, word-level timestamps)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  ✂️ Segment  │  Smart sentence-boundary detection (~60s chunks)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  🎬 Clip     │  FFmpeg stream-copy extraction (no re-encode)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  🧠 Summarize │  Groq LLaMA 3 (title + summary + bullets + tags)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  📦 Store    │  Local disk (dev) / Cloudflare R2 (prod)
  └──────┬──────┘
         ▼
    Study Reel 🎓
```

**Input:** A single YouTube URL  
**Output:** A scrollable reel of concept clips, each with:

- 🎬 A short video clip (45-90 seconds)
- 📌 An AI-generated concept title
- 💡 A one-liner summary
- 📝 3-4 bullet key points
- 🏷️ Topic tags

---

## 🛠️ Tech Stack

| Layer | Technology                | Purpose                                          |   Cost    |
| :---: | ------------------------- | ------------------------------------------------ | :-------: |
|  🌐   | **FastAPI**               | Async REST API + WebSocket server                |   Free    |
|  ⚙️   | **Celery + Redis**        | Distributed task queue for video processing      |   Free    |
|  🎤   | **OpenAI Whisper**        | Speech-to-text transcription (runs on local GPU) |   Free    |
|  🧠   | **Groq API** (LLaMA 3 8B) | AI summarization with structured JSON output     | Free tier |
|  📥   | **yt-dlp**                | YouTube video download with anti-bot measures    |   Free    |
|  🎬   | **FFmpeg**                | Video clip extraction via stream copy            |   Free    |
|  🗄️   | **SQLite** / PostgreSQL   | Relational database for all metadata             |   Free    |
|  📦   | **Cloudflare R2**         | Production clip storage (S3-compatible)          | Free 10GB |
|  🐳   | **Docker Compose**        | Local Redis infrastructure                       |   Free    |

### 💰 Total Running Cost: **$0/month**

Every component either runs locally on your hardware or uses a generous free tier. No credit card required.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser)                             │
│                                                                      │
│    test-ui/index.html  ←  WebSocket progress  ←  REST API calls      │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ HTTP / WebSocket
┌────────────────────────────────▼─────────────────────────────────────┐
│                        FASTAPI SERVER (:8000)                        │
│                                                                      │
│    POST /api/jobs         → Create job, enqueue Celery task          │
│    GET  /api/jobs/{id}    → Poll job status + progress %             │
│    GET  /api/reels/{id}   → Full reel data (segments + clips)        │
│    GET  /api/reels/{id}/notes → Aggregated structured notes          │
│    WS   /ws/jobs/{id}     → Real-time progress stream                │
│    GET  /health           → Health check                             │
│    GET  /docs             → Interactive Swagger UI                   │
└───────┬───────────────────────────────┬──────────────────────────────┘
        │                               │
┌───────▼───────┐            ┌──────────▼──────────────────────────────┐
│   SQLite DB   │            │          CELERY WORKER                  │
│               │            │                                         │
│  • jobs       │            │  Stage 1: yt-dlp download (720p)        │
│  • videos     │            │  Stage 2: Whisper transcribe (GPU)      │
│  • segments   │            │  Stage 3: Sentence-boundary segmentation│
│  • clips      │            │  Stage 4: FFmpeg clip extraction        │
│  • summaries  │            │  Stage 5: Groq AI summarization         │
│               │            │  Stage 6: Local / R2 storage            │
└───────────────┘            │  Stage 7: Mark job complete             │
                             └──────────────────┬──────────────────────┘
                                                │
                             ┌──────────────────▼──────────────────────┐
                             │           REDIS (:6379)                 │
                             │     Task broker + result backend        │
                             └─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Tool               | Install                                                       |
| ------------------ | ------------------------------------------------------------- |
| **Python 3.10+**   | [python.org](https://www.python.org/downloads/)               |
| **Docker Desktop** | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **FFmpeg**         | `winget install ffmpeg`                                       |
| **Groq API Key**   | Free at [console.groq.com](https://console.groq.com)          |

### 1. Clone & Configure

```bash
git clone https://github.com/Mohammedsami001/Clario.git
cd Clario/backend
cp .env.example .env
```

Edit `.env` and add your `GROQ_API_KEY`:

```env
GROQ_API_KEY=gsk_your_key_here
WHISPER_MODEL=base
WHISPER_DEVICE=cuda    # Use 'cpu' if no NVIDIA GPU
```

### 2. Start Redis

```bash
cd Clario
docker compose up redis -d
```

### 3. Install Dependencies

**Windows:**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate

# Install PyTorch (pick one):
pip install torch --index-url https://download.pytorch.org/whl/cu121   # NVIDIA GPU
pip install torch --index-url https://download.pytorch.org/whl/cpu     # CPU only

# Install everything else:
pip install openai-whisper
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install torch openai-whisper
pip install -r requirements.txt
```

### 4. Run (2 Terminals)

**Terminal 1 — API Server:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Look for: `Clario API started — tables ready`

**Terminal 2 — Celery Worker:**

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info --pool=solo
```

✅ Look for: `celery@... ready.`

### 5. Test

Open `test-ui/index.html` in your browser → paste a YouTube URL → hit **Generate Study Reel** → watch the magic happen.

Interactive API docs: **http://localhost:8000/docs**

---

## 📡 API Endpoints

### Jobs

| Method | Endpoint         | Description                                   |
| :----: | ---------------- | --------------------------------------------- |
| `POST` | `/api/jobs`      | Submit a YouTube URL → starts the pipeline    |
| `GET`  | `/api/jobs/{id}` | Poll job status, stage, and progress (0-100%) |
| `GET`  | `/api/jobs`      | List all jobs (most recent first)             |

**Create a job:**

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

**Response:**

```json
{
  "id": "3a102508-5121-48b5-9b11-69cded2b8e04",
  "status": "pending",
  "stage": null,
  "progress": 0,
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "created_at": "2026-05-01T10:30:00Z"
}
```

### Reels

| Method | Endpoint                    | Description                                                       |
| :----: | --------------------------- | ----------------------------------------------------------------- |
| `GET`  | `/api/reels/{job_id}`       | Full reel: video metadata + all segments with clips and summaries |
| `GET`  | `/api/reels/{job_id}/notes` | Aggregated notes for all segments                                 |

### WebSocket

| Protocol | Endpoint            | Description                                  |
| :------: | ------------------- | -------------------------------------------- |
|   `WS`   | `/ws/jobs/{job_id}` | Real-time progress stream (polls every 1.5s) |

**WebSocket message format:**

```json
{
  "job_id": "3a102508-...",
  "status": "processing",
  "stage": "Transcribing audio...",
  "progress": 25,
  "error_msg": null
}
```

### Health

| Method | Endpoint  | Description          |
| :----: | --------- | -------------------- |
| `GET`  | `/health` | Service health check |

---

## 🧠 The AI Pipeline

The pipeline is implemented as a single Deep Module (`app/pipeline/processor.py`) that encapsulates these 6 conceptual stages. It hides internal state transitions and emits Domain Events to a decoupled `ProjectRepository` interface.

### Stage 1: Download

- **Tool:** yt-dlp (latest, auto-updated)
- **Resolution:** 720p max (quality/speed balance)
- **Anti-bot:** User-Agent spoofing, browser cookie extraction (Chrome → Edge → Firefox), 5 retries
- **Output:** `temp/{job_id}/source.mp4`

### Stage 2: Transcribe

- **Tool:** OpenAI Whisper (`base` model)
- **Hardware:** NVIDIA GPU (CUDA + fp16) or CPU fallback
- **Features:** Word-level timestamps, VAD for silence detection
- **Output:** Full transcript + word array with `{word, start, end}`

### Stage 3: Segment

- **Strategy:** Time-based windowing with smart sentence-boundary detection
- **Target:** ~60 second segments (configurable via `SEGMENT_DURATION`)
- **Intelligence:** Finds nearest sentence break (`.` `?` `!`) within a ±10 second window — never cuts mid-sentence
- **Guard rail:** Max 20 segments per video (`MAX_SEGMENTS`)

### Stage 4: Clip

- **Tool:** FFmpeg with stream copy (`-c copy`) — no re-encoding
- **Speed:** Near-instant extraction (just copies bytes)
- **Output:** `temp/{job_id}/clips/clip_000.mp4`

### Stage 5: Summarize

- **Tool:** Groq API with `llama3-8b-8192`
- **Output format:** Structured JSON with `title`, `summary`, `bullets[]`, `tags[]`
- **Temperature:** 0.3 (deterministic, factual output)
- **Fallback:** If Groq fails, extracts first sentence as summary
- **Rate limit:** 14,400 requests/day (free tier) — supports 700+ videos/day

### Stage 6: Store

- **Dev mode:** Copies clips to `media/clips/` → served via FastAPI static files
- **Prod mode:** Uploads to Cloudflare R2 (S3-compatible) → returns public URL
- **Cleanup:** Deletes temp files after processing to save disk space

---

## 📂 Project Structure

```
Clario/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point, CORS, static files
│   │   ├── api/
│   │   │   ├── jobs.py             # Job CRUD endpoints
│   │   │   ├── reels.py            # Reel & notes retrieval
│   │   │   └── ws.py               # WebSocket live progress
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic settings (from .env)
│   │   │   └── database.py         # SQLAlchemy engine & session
│   │   ├── models/
│   │   │   └── models.py           # ORM: Job, Video, Segment, Clip, Summary
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   └── processor.py        # Deep module orchestrating all AI stages
│   │   ├── repository/
│   │   │   ├── project_repository.py      # Persistence interface (Domain Events)
│   │   │   └── sqlalchemy_repository.py   # PostgreSQL/SQLite implementation
│   │   └── tasks/
│   │       ├── celery_app.py       # Celery configuration
│   │       └── process_video.py    # Celery task entrypoint
│   ├── requirements.txt
│   ├── .env.example
│   ├── setup.bat                   # Windows one-click setup
│   ├── start_api.bat               # Start FastAPI server
│   └── start_worker.bat            # Start Celery worker
│
├── test-ui/
│   └── index.html                  # Dark-mode test interface
│
├── docker-compose.yml              # Redis service
├── push_to_github.bat              # Git push automation
├── .gitignore
└── README.md
```

---

## 🗄️ Database Schema

```sql
jobs         →  tracks pipeline status, progress %, error messages
videos       →  source metadata (title, duration, transcript, YouTube URL)
segments     →  concept chunks (index, title, start/end time, transcript)
clips        →  video files (local path or R2 URL, duration)
summaries    →  AI output (one-liner, bullet points, topic tags)
```

**Relationships:**

```
Job  1──1  Video  1──*  Segment  1──1  Clip  1──1  Summary
```

---

## ⚙️ Configuration

All settings via `.env` — see `.env.example` for defaults:

| Variable           | Default                    | Description                                                            |
| ------------------ | -------------------------- | ---------------------------------------------------------------------- |
| `DATABASE_URL`     | `sqlite:///./clario.db`    | Database connection string                                             |
| `REDIS_URL`        | `redis://localhost:6379/0` | Celery broker URL                                                      |
| `GROQ_API_KEY`     | —                          | **Required.** Get free at [console.groq.com](https://console.groq.com) |
| `WHISPER_MODEL`    | `base`                     | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`)        |
| `WHISPER_DEVICE`   | `cuda`                     | `cuda` for NVIDIA GPU, `cpu` for CPU-only                              |
| `SEGMENT_DURATION` | `60`                       | Target segment length in seconds                                       |
| `MAX_SEGMENTS`     | `20`                       | Maximum segments per video                                             |
| `BASE_URL`         | `http://localhost:8000`    | API base URL (for local clip URLs)                                     |

---

## 🧪 Test UI

The included `test-ui/index.html` provides a complete dark-mode test interface with:

- 🔗 YouTube URL input
- 📊 Real-time progress bar via WebSocket
- 🏷️ Status badges (pending → processing → done/failed)
- 🎬 Video player for each generated clip
- 📌 AI-generated titles, summaries, and bullet points
- 🏷️ Topic tags
- 📝 Full notes view with export capability

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with Precision by [SAMI](https://github.com/Mohammedsami001)**

_Clario MVP_
</div>
