# ⚡ Clario — AI Study Reel Generator

> Turn any YouTube lecture into a scrollable study reel — one concept at a time.

Clario takes a YouTube URL, transcribes it, segments it into concepts, generates short clips, and presents them in a TikTok-style vertical reel with AI summaries and bullet points.

---

## 🚀 Tech Stack

| Layer | Tool |
|---|---|
| Backend API | FastAPI (Python) |
| Task Queue | Celery + Redis |
| Transcription | faster-whisper (CUDA) |
| Summarization | Groq API (llama3-8b-8192) |
| Video Download | yt-dlp |
| Clip Generation | FFmpeg |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Storage | Local disk (dev) / Cloudflare R2 (prod) |

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.10+
- Docker Desktop (for Redis)
- FFmpeg on PATH (`winget install ffmpeg`)

### 1. Clone & configure
```bash
git clone https://github.com/Mohammedsami001/Clario.git
cd Clario/backend
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Start Redis
```bash
docker compose up redis -d
```

### 3. Install dependencies
```bash
# Windows
.\setup.bat

# Mac/Linux
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run (2 terminals)
```bash
# Terminal 1 — API server
.\start_api.bat        # → http://localhost:8000

# Terminal 2 — Celery worker
.\start_worker.bat
```

### 5. Test UI
Open `test-ui/index.html` in your browser.

---

## 📂 Project Structure

```
Clario/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes (jobs, reels, websocket)
│   │   ├── core/         # Config, database
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── pipeline/     # download → transcribe → segment → clip → summarize → store
│   │   └── tasks/        # Celery task orchestration
│   ├── requirements.txt
│   └── .env.example
├── test-ui/
│   └── index.html        # Simple browser test interface
└── docker-compose.yml
```

---

## 🗺️ Pipeline

```
YouTube URL
  → yt-dlp download (720p)
  → faster-whisper transcription (CUDA)
  → Time-based segmentation (60s chunks)
  → FFmpeg clip extraction
  → Groq AI summarization (llama3-8b)
  → Local / R2 storage
  → REST API + WebSocket → Test UI
```

---

## 📄 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/jobs` | Submit YouTube URL, start pipeline |
| `GET` | `/api/jobs/{id}` | Poll job status & progress |
| `GET` | `/api/reels/{id}` | Get full reel (clips + summaries) |
| `GET` | `/api/reels/{id}/notes` | Get aggregated notes |
| `WS` | `/ws/jobs/{id}` | Real-time progress stream |
| `GET` | `/health` | Health check |

Interactive docs: `http://localhost:8000/docs`

---

## 🔑 Environment Variables

See `.env.example` for all variables. Key ones:

```env
GROQ_API_KEY=         # Get free at console.groq.com
WHISPER_DEVICE=cuda   # Use 'cpu' if no GPU
DATABASE_URL=sqlite:///./clario.db
REDIS_URL=redis://localhost:6379/0
```

---

*Built with ❤️ — Clario MVP v0.1*
