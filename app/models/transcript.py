from typing import List
from pydantic import BaseModel, Field

class TranscriptSegment(BaseModel):
    id: int
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Original transcribed text")

class TranscriptData(BaseModel):
    source_language: str
    duration: float
    segments: List[TranscriptSegment]

class TranslationSegment(BaseModel):
    id: int
    start: float
    end: float
    source_text: str
    translated_text: str

class TranslationData(BaseModel):
    source_language: str
    target_language: str
    segments: List[TranslationSegment]