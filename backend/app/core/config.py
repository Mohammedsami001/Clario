from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./clario.db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Groq
    GROQ_API_KEY: str = ""

    # Cloudflare R2 (optional — uses local disk if blank)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "clario-clips"
    R2_PUBLIC_URL: Optional[str] = None

    # App
    BASE_URL: str = "http://localhost:8000"
    MEDIA_DIR: str = "media"
    TEMP_DIR: str = "temp"

    # Whisper — RTX 3050 supports cuda + float16
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cuda"
    WHISPER_COMPUTE_TYPE: str = "float16"

    # Segmentation
    SEGMENT_DURATION: int = 60
    MAX_SEGMENTS: int = 20

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
