import asyncio
from pathlib import Path
from typing import List
from app.models.transcript import TranslationSegment
from app.services.ffmpeg import FFmpegService
from app.services.tts.base import TTSProvider
from app.core.config import settings
from app.utils.logger import logger

class AudioSynchronizationService:
    @classmethod
    async def build_synchronized_audio(
        cls,
        segments: List[TranslationSegment],
        tts_provider: TTSProvider,
        voice_id: str,
        temp_dir: Path,
        output_dubbed_wav: Path,
        total_video_duration: float
    ) -> Path:
        temp_dir.mkdir(parents=True, exist_ok=True)
        raw_tts_dir = temp_dir / "tts_raw"
        stretched_dir = temp_dir / "tts_stretched"
        raw_tts_dir.mkdir(exist_ok=True)
        stretched_dir.mkdir(exist_ok=True)

        synced_segment_paths: List[Path] = []
        
        for seg in segments:
            target_duration = max(0.5, seg.end - seg.start)
            raw_seg_path = raw_tts_dir / f"seg_{seg.id}.mp3"
            
            # Step 1: Synthesize audio for segment
            await tts_provider.generate_audio(seg.translated_text, voice_id, raw_seg_path)
            
            # Step 2: Measure real TTS duration
            synth_duration = await FFmpegService.get_audio_duration(raw_seg_path)
            
            # Step 3: Compute intelligent speed factor
            speed_factor = synth_duration / target_duration
            
            # Clamp speed factor to keep natural human speech
            clamped_speed = max(
                settings.MIN_SPEED_FACTOR, 
                min(settings.MAX_SPEED_FACTOR, speed_factor)
            )
            
            stretched_seg_path = stretched_dir / f"seg_{seg.id}.wav"
            if abs(clamped_speed - 1.0) > 0.03:
                await FFmpegService.time_stretch_audio(raw_seg_path, stretched_seg_path, clamped_speed)
            else:
                # Convert directly to WAV
                await FFmpegService.extract_audio(raw_seg_path, stretched_seg_path, sample_rate=24000)
                
            synced_segment_paths.append(stretched_seg_path)

        # Step 4: Assemble final continuous audio timeline with exact timestamp alignments
        return await cls._assemble_timeline(
            segments=segments,
            audio_files=synced_segment_paths,
            output_wav=output_dubbed_wav,
            total_duration=total_video_duration,
            temp_dir=temp_dir
        )

    @classmethod
    async def _assemble_timeline(
        cls,
        segments: List[TranslationSegment],
        audio_files: List[Path],
        output_wav: Path,
        total_duration: float,
        temp_dir: Path
    ) -> Path:
        """
        Builds a master audio timeline matching the video duration using FFmpeg adelay & amix.
        """
        if not segments:
            return await FFmpegService.create_silent_wav(total_duration, output_wav)

        filter_inputs = []
        filter_complex_parts = []
        
        # Build inputs and delay filters
        for idx, (seg, audio_path) in enumerate(zip(segments, audio_files)):
            filter_inputs.extend(["-i", str(audio_path)])
            delay_ms = int(seg.start * 1000)
            filter_complex_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[a{idx}]")

        # Mix all delayed audio streams into one master audio track
        all_stream_labels = "".join([f"[a{i}]" for i in range(len(segments))])
        mix_str = f"{all_stream_labels}amix=inputs={len(segments)}:dropout_transition=0:normalize=0[mixed]"
        filter_complex_parts.append(mix_str)
        
        filter_complex = ";".join(filter_complex_parts)
        
        cmd = [
            "ffmpeg", "-y",
            *filter_inputs,
            "-filter_complex", filter_complex,
            "-map", "[mixed]",
            "-ac", "2",
            "-ar", "44100",
            "-t", f"{total_duration:.3f}",
            str(output_wav)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"Timeline assembly error: {stderr.decode()}")
            raise RuntimeError("خطا در هماهنگ‌سازی و مونتاژ نهایی لاین صوتی دوبله.")
            
        return output_wav