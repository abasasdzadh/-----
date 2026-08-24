from app.services.tts.base import TTSProvider
from app.services.tts.edge_tts_provider import EdgeTTSProvider

def get_tts_provider(provider_type: str = "edge") -> TTSProvider:
    if provider_type == "edge":
        return EdgeTTSProvider()
    raise ValueError(f"موتور TTS با نام {provider_type} پشتیبانی نمی‌شود.")