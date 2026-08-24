import asyncio
from pathlib import Path
from typing import Optional, List
from faster_whisper import WhisperModel
from app.core.config import settings
from app.core.hardware import get_system_hardware_info
from app.models.transcript import TranscriptSegment, TranscriptData
from app.utils.logger import logger

class TranscriptionService:
    _model_instance: Optional[WhisperModel] = None

    @classmethod
    def get_model(cls) -> WhisperModel:
        if cls._model_instance is None:
            hw = get_system_hardware_info()
            device = settings.WHISPER_DEVICE
            if device == "auto":
                device = hw["recommended_device"]
            compute_type = settings.WHISPER_COMPUTE_TYPE
            model_name = settings.WHISPER_MODEL or hw["recommended_whisper_model"]
            
            logger.info(f"Loading faster-whisper model '{model_name}' on {device} ({compute_type})...")
            cls._model_instance = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                download_root=str(settings.STORAGE_DIR / "models" / "whisper")
            )
        return cls._model_instance

    @classmethod
    async def transcribe(
        cls, 
        audio_path: Path, 
        source_language: Optional[str] = None
    ) -> TranscriptData:
        loop = asyncio.get_running_loop()
        
        def _run_whisper():
            model = cls.get_model()
            lang = None if not source_language or source_language.lower() == "auto" else source_language
            
            segments, info = model.transcribe(
                str(audio_path),
                language=lang,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                beam_size=5
            )
            
            result_segments: List[TranscriptSegment] = []
            segment_id = 1
            for seg in segments:
                cleaned_text = seg.text.strip()
                if cleaned_text:
                    result_segments.append(
                        TranscriptSegment(
                            id=segment_id,
                            start=round(seg.start, 2),
                            end=round(seg.end, 2),
                            text=cleaned_text
                        )
                    )
                    segment_id += 1
                    
            return TranscriptData(
                source_language=info.language or "unknown",
                duration=round(info.duration, 2),
                segments=result_segments
            )

        return await loop.run_in_executor(None, _run_whisper)