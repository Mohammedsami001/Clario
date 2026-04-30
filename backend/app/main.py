import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import create_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Clario API",
    description="AI Study Reel Generator — Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local media files (clips) during development
os.makedirs(os.path.join(settings.MEDIA_DIR, "clips"), exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

# Routers
from app.api import jobs, reels, ws  # noqa: E402
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(reels.router, prefix="/api/reels", tags=["reels"])
app.include_router(ws.router, prefix="/ws", tags=["websocket"])


@app.on_event("startup")
def on_startup():
    create_tables()
    logging.getLogger(__name__).info("✅ Clario API started — tables ready")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "clario-api", "version": "0.1.0"}
