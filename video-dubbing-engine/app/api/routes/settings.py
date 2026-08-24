from fastapi import APIRouter
from app.core.config import settings, get_effective_gemini_key, set_runtime_gemini_key
from app.core.hardware import get_system_hardware_info
from app.core.security import mask_api_key
from app.models.job import SettingsUpdateRequest, SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=SettingsResponse)
async def get_settings():
    current_key = get_effective_gemini_key()
    return SettingsResponse(
        gemini_api_key_configured=bool(current_key),
        gemini_api_key_masked=mask_api_key(current_key),
        whisper_model=settings.WHISPER_MODEL,
        whisper_device=settings.WHISPER_DEVICE,
        hardware=get_system_hardware_info()
    )

@router.post("/gemini-key")
async def update_gemini_key(req: SettingsUpdateRequest):
    if req.gemini_api_key is not None:
        set_runtime_gemini_key(req.gemini_api_key)
    return {"status": "success", "configured": bool(get_effective_gemini_key())}