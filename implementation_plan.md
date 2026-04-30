# Quickcept — AI Study Reel Generator
### Senior Product + Engineering Plan · Zero-Cost MVP → YC-Ready SaaS

---

> **What we're building:** A web app that takes any YouTube lecture and turns it into a TikTok-style vertical scroll of 30-second concept clips, each with an AI-generated summary and bullet points — so students never sit through a boring 2-hour lecture again.

---

## 1. PRD Critique & Fixes

### ✅ What's solid
- Core loop (input → transcribe → segment → clip → reel) is correct
- Tech stack choices (yt-dlp, Whisper, FFmpeg) are free and battle-tested
- Scope restriction is smart — local LLM for summaries avoids API costs

### ⚠️ Issues I'm fixing in this plan

| Issue | Fix |
|---|---|
| No auth layer defined | Add Clerk (free tier) — needed to track user history & link sessions to jobs |
| No job queue / async model | A 30-min video can't be processed in a single HTTP request. Need a task queue (Celery + Redis or BullMQ) |
| FFmpeg clips stored where? | Need a defined storage strategy: local disk → Cloudflare R2 (free 10 GB) |
| No database schema beyond MVP | Extended schema with `jobs`, `users`, `videos`, `segments`, `clips` tables |
| No error recovery | Pipeline stages need retry logic and partial-result saving |
| Mobile-first reel UI underspecified | Defined below: TikTok-clone vertical scroll with keyboard + swipe support |
| "15–45 second clips" too vague | Target **45–90 seconds** — shorter clips lose educational context; longer keeps engagement |
| No landing page / waitlist | Need a high-converting landing page before launch for YC traction |
| Ollama on server = huge RAM cost | Use Groq API (free tier: 14,400 requests/day with Llama 3) instead of local Ollama |

---

## 2. Revised Tech Stack (100% Free Tier)

| Layer | Tool | Why / Cost |
|---|---|---|
| **Frontend** | Next.js 14 (App Router) | Free, SSR, great DX |
| **Styling** | Tailwind CSS + shadcn/ui | Free, fast, accessible |
| **Auth** | Clerk | Free up to 10,000 MAU |
| **Backend API** | FastAPI (Python) | Async-native, perfect for ML pipelines |
| **Task Queue** | Celery + Redis | Open source; Redis Cloud free 30MB |
| **Transcription** | faster-whisper (local, base model) | Free, runs on CPU |
| **Summarization** | Groq API (llama3-8b-8192) | Free tier: 14,400 req/day |
| **Video Download** | yt-dlp | Free, open source |
| **Clip Generation** | FFmpeg | Free, open source |
| **Database** | PostgreSQL via Supabase | Free 500MB |
| **File Storage** | Cloudflare R2 | Free 10GB storage, free egress |
| **Deployment (BE)** | Railway.app | Free $5 credit/month = ~500 hrs |
| **Deployment (FE)** | Vercel | Free hobby tier |
| **Monitoring** | Sentry | Free 5k errors/month |

**Total recurring cost: $0/month for MVP scale**

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vercel)                        │
│   Next.js 14  ·  Clerk Auth  ·  Tailwind  ·  shadcn/ui         │
│                                                                  │
│   /           Landing Page + Waitlist                            │
│   /dashboard  User's reels history                               │
│   /process    Submit YouTube URL / Upload                        │
│   /reel/[id]  The TikTok-style scrollable reel                   │
│   /notes/[id] Full structured notes export                       │
└─────────────────────┬───────────────────────────────────────────┘
                       │ HTTPS REST / WebSocket (job status)
┌─────────────────────▼───────────────────────────────────────────┐
│                    BACKEND API (Railway)                         │
│                    FastAPI + Python 3.11                         │
│                                                                  │
│   POST /api/jobs        → Create job, enqueue task               │
│   GET  /api/jobs/{id}   → Job status + progress %               │
│   GET  /api/reels/{id}  → Reel data (segments + clips)          │
│   GET  /api/notes/{id}  → Aggregated notes                      │
│   WS   /ws/jobs/{id}    → Real-time progress stream             │
└──────┬─────────────────────────┬───────────────────────────────┘
       │                         │
┌──────▼──────┐       ┌──────────▼──────────────────────────────┐
│  PostgreSQL  │       │         Celery Worker (Railway)          │
│  (Supabase)  │       │                                          │
│              │       │  Stage 1: yt-dlp download               │
│  users       │       │  Stage 2: faster-whisper transcribe     │
│  jobs        │       │  Stage 3: Segment (time-based MVP)      │
│  videos      │       │  Stage 4: FFmpeg clip extraction        │
│  segments    │       │  Stage 5: Groq summarize each segment   │
│  clips       │       │  Stage 6: Upload clips → R2             │
│  summaries   │       │  Stage 7: Mark job complete             │
└──────────────┘       └──────────────────────────────────────────┘
                                        │
                            ┌───────────▼────────────┐
                            │    Cloudflare R2        │
                            │   (Video clip storage)  │
                            └─────────────────────────┘
```

---

## 4. Database Schema (Full)

```sql
-- Users (synced from Clerk webhook)
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_id    TEXT UNIQUE NOT NULL,
  email       TEXT NOT NULL,
  name        TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Jobs: one per video submission
CREATE TABLE jobs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id),
  status      TEXT DEFAULT 'pending', -- pending|processing|done|failed
  stage       TEXT,                   -- current pipeline stage
  progress    INT DEFAULT 0,          -- 0-100
  error_msg   TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Videos: metadata about the source
CREATE TABLE videos (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id      UUID REFERENCES jobs(id) UNIQUE,
  title       TEXT,
  duration    INT,               -- seconds
  source_url  TEXT,              -- YouTube URL or 'upload'
  raw_path    TEXT,              -- temp local path
  transcript  TEXT,              -- full transcript text
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Segments: concept chunks from the transcript
CREATE TABLE segments (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id    UUID REFERENCES videos(id),
  index       INT,               -- ordering
  title       TEXT,
  start_time  FLOAT,             -- seconds
  end_time    FLOAT,             -- seconds
  transcript  TEXT               -- segment-level transcript
);

-- Clips: actual video files
CREATE TABLE clips (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  segment_id  UUID REFERENCES segments(id),
  r2_key      TEXT,              -- Cloudflare R2 object key
  public_url  TEXT,
  duration    FLOAT
);

-- Summaries: AI output per clip
CREATE TABLE summaries (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_id     UUID REFERENCES clips(id),
  one_liner   TEXT,
  bullet_points JSONB,           -- ["point 1", "point 2", ...]
  topic_tags  JSONB              -- ["thermodynamics", "entropy"]
);
```

---

## 5. Pipeline Design (Deep Dive)

### Stage 1 — Video Acquisition
```
Input: YouTube URL or .mp4 upload
Tool: yt-dlp
Output: /tmp/{job_id}/source.mp4

Rules:
- Max duration: 3 hours (guard rail)
- Download 720p max (balance quality vs. disk)
- On upload: store directly, skip yt-dlp
```

### Stage 2 — Transcription
```
Tool: faster-whisper (base model, CPU)
Output: List of Word objects with timestamps
Format: [{word, start, end}, ...]

Optimization:
- Use VAD filter to skip silence
- base model: good enough for MVP, ~10x realtime on CPU
- Store full transcript as text + raw word-level JSON
```

### Stage 3 — Segmentation (MVP: Time-Based)
```
Strategy: Fixed window with smart boundary detection
- Target segment duration: 60 seconds
- Find nearest sentence break (period/newline) within ±10 seconds
- Never cut mid-sentence

Output: [{index, title, start, end, transcript}, ...]

Title generation: First ~8 words of the segment transcript
Advanced (Phase 2): Send transcript to Groq and ask for topic boundaries
```

### Stage 4 — Clip Extraction
```
Tool: FFmpeg
Command: ffmpeg -ss {start} -to {end} -i source.mp4 -c copy out.mp4

Note: -c copy (no re-encode) = fast
Output: /tmp/{job_id}/clips/segment_{n}.mp4
```

### Stage 5 — Summarization
```
Tool: Groq API (llama3-8b-8192, free tier)
Prompt per segment:

  "Given this lecture transcript segment, generate:
   1. A single punchy title (max 8 words)
   2. One sentence summary
   3. 3-4 bullet key points
   Format as JSON: {title, summary, bullets: []}"

Rate limiting: 14,400 req/day → fine for MVP
Fallback: if Groq fails, extract first sentence as summary
```

### Stage 6 — Upload to R2
```
Tool: boto3 with R2 endpoint
Upload all clips to Cloudflare R2
Set public read ACL
Store public URL in clips table
Delete local temp files
```

---

## 6. Frontend Pages & UX

### 6.1 Landing Page (`/`)
- Headline: "Turn any lecture into a study reel"
- 15-second demo video/GIF of the product
- YouTube URL input with "Generate Reel" CTA
- Waitlist email capture (before auth)
- Social proof section (even fake metrics for launch)
- Dark mode, purple/indigo brand gradient

### 6.2 Processing Page (`/process/[jobId]`)
- Real-time progress bar (WebSocket)
- Stage labels: Downloading → Transcribing → Segmenting → Generating Clips → Summarizing → Done
- Estimated time remaining
- Redirect to reel when complete

### 6.3 Reel View (`/reel/[id]`)
```
TikTok-style vertical scroll
┌──────────────────────────┐
│                          │
│      VIDEO CLIP          │  ← auto-play, muted by default
│      (16:9 or 9:16)      │
│                          │
├──────────────────────────┤
│  ⏱ 0:45  Concept 3/12   │  ← progress indicator
├──────────────────────────┤
│  📌 Entropy and Disorder │  ← AI title
│  One-liner summary here  │  ← AI summary
├──────────────────────────┤
│  • Entropy always inc... │
│  • Work → heat, not ...  │  ← AI bullet points
│  • Delta S > 0 for ...   │
├──────────────────────────┤
│  [← Prev]  [Next →]      │
│  [📄 Notes] [🔗 Share]   │
└──────────────────────────┘

Keyboard: Arrow keys, Space to pause
Mobile: Swipe up/down
```

### 6.4 Notes View (`/notes/[id]`)
- All segments listed sequentially
- Title + timestamp + bullet points per segment
- "Copy All Notes" button
- "Export as PDF" button (jsPDF, client-side)
- Markdown export option

### 6.5 Dashboard (`/dashboard`)
- Grid of past reels (thumbnail + title)
- Processing status indicator
- Delete reel option

---

## 7. Development Phases (Revised)

### Phase 0 — Foundation (Days 1–3)
- [ ] Init Next.js 14 app in `d:\quickcept\frontend`
- [ ] Init FastAPI app in `d:\quickcept\backend`
- [ ] Set up Supabase project + run schema migration
- [ ] Set up Clerk, connect to Next.js
- [ ] Set up Cloudflare R2 bucket
- [ ] Set up Railway project for backend + Redis
- [ ] Configure env vars

### Phase 1 — Backend Pipeline (Days 4–8)
- [ ] yt-dlp download service
- [ ] faster-whisper transcription service
- [ ] Time-based segmentation logic
- [ ] FFmpeg clip extraction
- [ ] Groq summarization with prompt engineering
- [ ] R2 upload service
- [ ] Celery task chain wiring all stages
- [ ] Job CRUD APIs
- [ ] WebSocket for progress updates

### Phase 2 — Frontend Core (Days 9–14)
- [ ] Landing page with URL input
- [ ] Processing page with live progress
- [ ] Reel UI (vertical scroll, auto-play)
- [ ] Notes view
- [ ] Dashboard

### Phase 3 — Polish + Infra (Days 15–20)
- [ ] Error handling, retry logic
- [ ] Mobile responsiveness + swipe gestures
- [ ] Sentry integration
- [ ] Rate limiting (1 job per user at a time)
- [ ] File cleanup cron (delete source video after processing)
- [ ] SEO + OG tags
- [ ] Deploy to Vercel + Railway

### Phase 4 — Pre-Launch (Days 21–28)
- [ ] Beta test with 5–10 real students
- [ ] Record demo video
- [ ] Set up analytics (Posthog free tier)
- [ ] ProductHunt draft
- [ ] Twitter/X launch thread
- [ ] Submit to YC

---

## 8. Monorepo Structure

```
d:\quickcept\
├── frontend/                    # Next.js 14
│   ├── app/
│   │   ├── page.tsx             # Landing
│   │   ├── dashboard/page.tsx
│   │   ├── process/[jobId]/page.tsx
│   │   ├── reel/[id]/page.tsx
│   │   └── notes/[id]/page.tsx
│   ├── components/
│   │   ├── ui/                  # shadcn components
│   │   ├── ReelPlayer.tsx
│   │   ├── ProgressTracker.tsx
│   │   ├── NotesView.tsx
│   │   └── LandingHero.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── websocket.ts
│   └── ...
│
├── backend/                     # FastAPI + Celery
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── api/
│   │   │   ├── jobs.py
│   │   │   └── reels.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── pipeline/
│   │   │   ├── download.py      # yt-dlp
│   │   │   ├── transcribe.py    # faster-whisper
│   │   │   ├── segment.py       # time-based segmentation
│   │   │   ├── clip.py          # FFmpeg
│   │   │   ├── summarize.py     # Groq API
│   │   │   └── storage.py       # R2 upload
│   │   └── tasks/
│   │       └── process_video.py # Celery task chain
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml           # Local dev (backend + redis + postgres)
├── .env.example
└── README.md
```

---

## 9. Environment Variables

```env
# Backend
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
GROQ_API_KEY=gsk_...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=quickcept-clips
R2_PUBLIC_URL=https://pub-xxx.r2.dev

# Frontend
NEXT_PUBLIC_API_URL=https://api.quickcept.app
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
```

---

## 10. Zero-Cost Free Tier Limits & Guardrails

| Service | Free Limit | Guardrail We Add |
|---|---|---|
| Groq | 14,400 req/day | Max 20 segments/video |
| Cloudflare R2 | 10 GB storage | Auto-delete clips after 30 days |
| Railway | $5/month credit | Auto-pause workers after idle |
| Supabase | 500 MB DB | Compress transcript JSON |
| Vercel | 100 GB bandwidth | Serve clips from R2, not Vercel |
| Clerk | 10,000 MAU | Fine for MVP |

---

## 11. YC Application Alignment

> YC funds companies with **a clear problem, a sharp solution, and early traction**.

| YC Criterion | How Quickcept Hits It |
|---|---|
| **Problem** | 2-hour YouTube lectures kill retention. Students hate scrubbing. |
| **Solution** | Auto-generate structured 60-second concept reels |
| **Market** | 300M+ students globally; EdTech is a proven vertical |
| **Founder insight** | You're the user — you know the pain |
| **Traction** | 100 users in Week 1 from one Twitter post = credible signal |
| **Tech differentiation** | End-to-end pipeline: no competitor does clip+summary+reel |
| **Revenue model** | Freemium: 3 reels/month free, $9/month unlimited |

### Revenue Tiers (add after MVP)
```
Free:       3 reels/month, 30-min max
Student:    $5/month, 20 reels, 2hr max
Pro:        $12/month, unlimited, 4hr max, PDF export, priority queue
Team:       $29/month, 5 users, shared dashboard
```

---

## 12. Open Questions Before We Start Coding

> [!IMPORTANT]
> **Please answer these before I begin building:**

1. **Brand Name**: Stick with **Quickcept** or prefer **Clario**? (affects domain, logo, colors)
2. **Start where?** Do you want me to start with:
   - **A)** The backend pipeline first (yt-dlp + Whisper + Groq), OR
   - **B)** The frontend landing page + reel UI first (visual-first, build hype while backend builds)
   - **C)** Both in parallel (recommended if you have 2 terminals)
3. **Python version?** Run `python --version` in your terminal and paste the result
4. **Groq API key?** Go to [console.groq.com](https://console.groq.com) and get a free key — you'll need this for summaries
5. **GPU available?** Run `nvidia-smi` — if you have a GPU, whisper runs 10x faster; we optimize accordingly
6. **File Upload**: For MVP, should we support MP4 upload, or **YouTube URL only** to keep scope tight?

---

## 13. What I'll Build First (Once Approved)

Once you answer the questions above, my execution order is:

1. `docker-compose.yml` for local dev (Postgres + Redis)
2. FastAPI backend skeleton + database models
3. Full Celery pipeline (download → transcribe → segment → clip → summarize → upload)
4. REST API + WebSocket endpoints
5. Next.js frontend with all 5 pages
6. Deploy to Vercel + Railway

**Estimated build time: 3–4 focused days of coding**

---

*Plan authored by Antigravity · Zero-cost, YC-ready approach · Ready to execute on approval*
