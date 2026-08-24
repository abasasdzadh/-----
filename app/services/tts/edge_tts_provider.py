import edge_tts
from pathlib import Path
from typing import List, Dict, Any
from app.services.tts.base import TTSProvider
from app.utils.logger import logger

class EdgeTTSProvider(TTSProvider):
    """
    High-quality, free, open-source TTS provider supporting 80+ languages including Persian.
    Requires zero GPU VRAM and no API keys.
    """
    
    VOICE_DEFAULTS = {
        "fa": "fa-IR-FaridNeural",
        "fa-IR": "fa-IR-FaridNeural",
        "en": "en-US-GuyNeural",
        "ar": "ar-SA-HamedNeural",
        "tr": "tr-TR-AhmetNeural",
        "de": "de-DE-ConradNeural",
        "fr": "fr-FR-HenriNeural",
        "es": "es-ES-AlvaroNeural"
    }

    async def generate_audio(
        self,
        text: str,
        voice_id: str,
        output_path: Path
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        clean_text = text.strip()
        if not clean_text:
            clean_text = "."

        communicate = edge_tts.Communicate(clean_text, voice_id)
        await communicate.save(str(output_path))
        return output_path

    async def get_available_voices(self, target_language: str = None) -> List[Dict[str, Any]]:
        voices = await edge_tts.list_voices()
        result = []
        lang_filter = target_language.lower().split("-")[0] if target_language else None
        
        for v in voices:
            short_name = v.get("ShortName", "")
            locale = v.get("Locale", "").lower()
            gender = v.get("Gender", "")
            
            if lang_filter and not locale.startswith(lang_filter):
                continue
                
            result.append({
                "id": short_name,
                "name": f"{short_name} ({gender})",
                "gender": gender,
                "locale": v.get("Locale", "")
            })
        return result