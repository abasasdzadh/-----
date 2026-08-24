from fastapi import APIRouter, HTTPException
from app.models.job import VideoInspectRequest, VideoInspectResponse
from app.services.youtube import YouTubeService
from app.services.tts.factory import get_tts_provider

router = APIRouter(prefix="/video", tags=["video"])

@router.post("/inspect", response_model=VideoInspectResponse)
async def inspect_video(request: VideoInspectRequest):
    data = await YouTubeService.inspect_video(request.url)
    return VideoInspectResponse(**data)

@router.get("/voices")
async def list_voices(target_language: str = "fa"):
    provider = get_tts_provider("edge")
    voices = await provider.get_available_voices(target_language)
    return {"voices": voices}