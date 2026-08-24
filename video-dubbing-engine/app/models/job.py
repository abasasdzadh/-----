from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.transcript import TranscriptSegment, TranslationSegment

class VideoInspectRequest(BaseModel):
    url: str

class VideoInspectResponse(BaseModel):
    url: str
    title: str
    duration: float
    duration_formatted: str
    thumbnail: str
    uploader: str
    available_qualities: List[str]

class JobCreateRequest(BaseModel):
    url: str
    source_language: str = "auto"
    target_language: str = "fa"
    voice_id: Optional[str] = None
    keep_original_audio: bool = False
    original_audio_volume: float = Field(0.2, ge=0.0, le=1.0)

class JobResponse(BaseModel):
    job_id: str
    url: str
    title: Optional[str] = None
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    source_language: str
    target_language: str
    voice_id: Optional[str] = None
    keep_original_audio: bool
    original_audio_volume: float
    status: str
    progress: float
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str

class JobEventMessage(BaseModel):
    job_id: str
    status: str
    progress: float
    current_step: str
    error_message: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None

class SettingsResponse(BaseModel):
    gemini_api_key_configured: bool
    gemini_api_key_masked: Optional[str]
    whisper_model: str
    whisper_device: str
    hardware: dict