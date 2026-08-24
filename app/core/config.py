import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
JOBS_DIR = STORAGE_DIR / "jobs"

# Ensure required directories exist
JOBS_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "Automated Video Dubbing Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Whisper STT
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "auto"
    WHISPER_COMPUTE_TYPE: str = "int8"
    
    # Engine limits
    MAX_CONCURRENT_JOBS: int = 2
    MAX_VIDEO_DURATION_SECONDS: int = 1800  # 30 mins
    DATABASE_PATH: Path = STORAGE_DIR / "dubbing_engine.db"
    
    # Time-stretch bounds for audio sync
    MIN_SPEED_FACTOR: float = 0.80
    MAX_SPEED_FACTOR: float = 1.35
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Dynamic in-memory override for runtime user-submitted API Key
_runtime_gemini_key: Optional[str] = None

def get_effective_gemini_key() -> Optional[str]:
    return _runtime_gemini_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

def set_runtime_gemini_key(key: str) -> None:
    global _runtime_gemini_key
    _runtime_gemini_key = key.strip() if key else None