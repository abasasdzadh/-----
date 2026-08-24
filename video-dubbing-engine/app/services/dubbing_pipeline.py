import json
import asyncio
from pathlib import Path
from typing import Callable, Awaitable
from app.core.config import settings
from app.core.database import update_job_record
from app.services.youtube import YouTubeService
from app.services.ffmpeg import FFmpegService
from app.services.transcription import TranscriptionService
from app.services.translation import TranslationService
from app.services.tts.factory import get_tts_provider
from app.services.tts.edge_tts_provider import EdgeTTSProvider
from app.services.synchronization import AudioSynchronizationService
from app.models.transcript import TranscriptData, TranslationData
from app.utils.logger import logger

ProgressCallback = Callable[[str, float, str], Awaitable[None]]

class DubbingPipeline:
    def __init__(self, job_dict: dict, on_progress: ProgressCallback):
        self.job = job_dict
        self.job_id = job_dict["id"]
        self.on_progress = on_progress
        self.job_dir = settings.JOBS_DIR / self.job_id
        
        # Subdirectories
        self.input_dir = self.job_dir / "input"
        self.audio_dir = self.job_dir / "audio"
        self.transcript_dir = self.job_dir / "transcript"
        self.translation_dir = self.job_dir / "translation"
        self.tts_dir = self.job_dir / "tts"
        self.output_dir = self.job_dir / "output"

        for d in [self.input_dir, self.audio_dir, self.transcript_dir, 
                  self.translation_dir, self.tts_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)

    async def execute(self):
        try:
            # 1. Inspect & Checkpoint
            await self.on_progress("downloading", 10.0, "در حال دریافت اطلاعات و دانلود ویدیوی اصلی...")
            video_input_file = self.input_dir / "source.mp4"
            if not video_input_file.exists():
                video_input_file = await YouTubeService.download_video(self.job["url"], video_input_file)
            
            video_duration = await FFmpegService.get_audio_duration(video_input_file)
            await update_job_record(self.job_id, {"duration": video_duration})

            # 2. Extract Audio
            await self.on_progress("extracting_audio", 25.0, "استخراج لاین صوتی با کیفیت بالا...")
            extracted_audio = self.audio_dir / "extracted_16k.wav"
            if not extracted_audio.exists():
                await FFmpegService.extract_audio(video_input_file, extracted_audio, sample_rate=16000)

            # 3. Speech to Text (Whisper) - Resume Support
            transcript_json_path = self.transcript_dir / "transcription.json"
            if transcript_json_path.exists():
                logger.info(f"Resuming job {self.job_id} from saved transcription artifact.")
                with open(transcript_json_path, "r", encoding="utf-8") as f:
                    transcript_data = TranscriptData(**json.load(f))
                await self.on_progress("transcribing", 45.0, "متن استخراج شده از مرحله قبل بارگذاری شد.")
            else:
                await self.on_progress("transcribing", 40.0, "تبدیل گفتار به متن با هوش مصنوعی Whisper...")
                transcript_data = await TranscriptionService.transcribe(
                    extracted_audio, 
                    source_language=self.job.get("source_language")
                )
                with open(transcript_json_path, "w", encoding="utf-8") as f:
                    json.dump(transcript_data.model_dump(), f, ensure_ascii=False, indent=2)

            if not transcript_data.segments:
                raise RuntimeError("هیچ گفتار قابل تشخیصی در این ویدیو یافت نشد.")

            # 4. Translation (Gemini) - Resume Support
            translation_json_path = self.translation_dir / "translation.json"
            if translation_json_path.exists():
                logger.info(f"Resuming job {self.job_id} from saved translation artifact.")
                with open(translation_json_path, "r", encoding="utf-8") as f:
                    translation_data = TranslationData(**json.load(f))
                await self.on_progress("translating", 65.0, "ترجمه ذخیره شده از مرحله قبل بارگذاری شد.")
            else:
                await self.on_progress("translating", 60.0, "ترجمه تخصصی و طبیعی جملات با Gemini AI...")
                target_lang = self.job.get("target_language", "fa")
                translation_data = await TranslationService.translate_transcript(
                    segments=transcript_data.segments,
                    source_lang=transcript_data.source_language,
                    target_lang=target_lang
                )
                with open(translation_json_path, "w", encoding="utf-8") as f:
                    json.dump(translation_data.model_dump(), f, ensure_ascii=False, indent=2)

            # 5. Voice Generation & Synchronization
            await self.on_progress("generating_voice", 75.0, "تولید صدای دوبله و همگام‌سازی زمانی (Lip-Sync/Timing)...")
            tts_provider = get_tts_provider("edge")
            voice_id = self.job.get("voice_id")
            if not voice_id:
                voice_id = EdgeTTSProvider.VOICE_DEFAULTS.get(
                    self.job.get("target_language", "fa"), "fa-IR-FaridNeural"
                )

            master_dubbed_wav = self.audio_dir / "master_dubbed.wav"
            await AudioSynchronizationService.build_synchronized_audio(
                segments=translation_data.segments,
                tts_provider=tts_provider,
                voice_id=voice_id,
                temp_dir=self.tts_dir,
                output_dubbed_wav=master_dubbed_wav,
                total_video_duration=video_duration
            )

            # 6. Final Video Rendering
            await self.on_progress("rendering", 90.0, "میکس صدا و رندر نهایی فایل MP4 با FFmpeg...")
            final_video_output = self.output_dir / "dubbed_final.mp4"
            await FFmpegService.render_dubbed_video(
                original_video=video_input_file,
                dubbed_audio=master_dubbed_wav,
                output_video=final_video_output,
                keep_original=self.job.get("keep_original_audio", False),
                original_vol=self.job.get("original_audio_volume", 0.2),
                dubbed_vol=1.0
            )

            # 7. Complete
            await self.on_progress("completed", 100.0, "دوبله ویدیو با موفقیت تکمیل شد.")

        except asyncio.CancelledError:
            logger.warning(f"Job {self.job_id} was cancelled.")
            await self.on_progress("cancelled", 0.0, "پردازش توسط کاربر لغو شد.")
            raise
        except Exception as e:
            logger.error(f"Error in job pipeline {self.job_id}: {str(e)}", exc_info=True)
            await self.on_progress("failed", 0.0, f"خطا در پردازش: {str(e)}")
            raise