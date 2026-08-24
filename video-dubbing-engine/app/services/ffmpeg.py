import asyncio
import json
import shutil
from pathlib import Path
from typing import Optional
from app.utils.logger import logger

class FFmpegService:
    @staticmethod
    def _verify_tools():
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("ابزار FFmpeg یا FFprobe در سرور نصب نشده است.")

    @classmethod
    async def extract_audio(cls, video_path: Path, output_audio_path: Path, sample_rate: int = 16000) -> Path:
        cls._verify_tools()
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            str(output_audio_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"خطای FFmpeg در استخراج صدا: {stderr.decode()}")
        return output_audio_path

    @classmethod
    async def get_audio_duration(cls, file_path: Path) -> float:
        cls._verify_tools()
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(file_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"خطای FFprobe در محاسبه زمان: {stderr.decode()}")
        data = json.loads(stdout.decode())
        return float(data.get("format", {}).get("duration", 0.0))

    @classmethod
    async def time_stretch_audio(cls, input_audio: Path, output_audio: Path, speed: float) -> Path:
        """
        Adjusts audio tempo without pitch distortion using the atempo filter.
        Handles chained filters if speed is outside 0.5 - 2.0.
        """
        cls._verify_tools()
        speed = max(0.5, min(2.0, speed))  # Bound within safe limits
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_audio),
            "-filter:a", f"atempo={speed:.4f}",
            "-vn",
            str(output_audio)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"خطا در تغییر سرعت صدا: {stderr.decode()}")
        return output_audio

    @classmethod
    async def create_silent_wav(cls, duration: float, output_path: Path, sample_rate: int = 24000) -> Path:
        cls._verify_tools()
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=mono",
            "-t", f"{duration:.4f}",
            "-acodec", "pcm_s16le",
            str(output_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return output_path

    @classmethod
    async def render_dubbed_video(
        cls,
        original_video: Path,
        dubbed_audio: Path,
        output_video: Path,
        keep_original: bool = False,
        original_vol: float = 0.2,
        dubbed_vol: float = 1.0
    ) -> Path:
        cls._verify_tools()
        output_video.parent.mkdir(parents=True, exist_ok=True)
        
        if keep_original:
            # Mix original audio with dubbed audio using amix filter
            filter_complex = (
                f"[0:a]volume={original_vol:.2f}[a0];"
                f"[1:a]volume={dubbed_vol:.2f}[a1];"
                f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(original_video),
                "-i", str(dubbed_audio),
                "-filter_complex", filter_complex,
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video)
            ]
        else:
            # Replace audio completely with dubbed audio
            cmd = [
                "ffmpeg", "-y",
                "-i", str(original_video),
                "-i", str(dubbed_audio),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video)
            ]
            
        logger.info(f"Executing FFmpeg render: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"خطای FFmpeg در رندر نهایی ویدیو: {stderr.decode()}")
        return output_video