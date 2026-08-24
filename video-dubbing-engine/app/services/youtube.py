import asyncio
from typing import Dict, Any
from pathlib import Path
import yt_dlp
from fastapi import HTTPException
from app.core.security import validate_youtube_url
from app.utils.logger import logger

class YouTubeService:
    @staticmethod
    def _format_seconds(seconds: float) -> str:
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    @classmethod
    async def inspect_video(cls, url: str) -> Dict[str, Any]:
        valid_url = validate_youtube_url(url)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True
        }
        
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(
                None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(valid_url, download=False)
            )
        except Exception as e:
            logger.error(f"Error inspecting video {url}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"امکان دریافت اطلاعات ویدیو وجود ندارد. ممکن است ویدیو خصوصی یا ناموجود باشد: {str(e)}"
            )

        duration = float(info.get("duration") or 0.0)
        
        # Collect available formats/resolutions
        formats = info.get("formats", [])
        qualities = set()
        for f in formats:
            if f.get("vcodec") != "none" and f.get("height"):
                qualities.add(f"{f.get('height')}p")
        sorted_qualities = sorted(list(qualities), key=lambda x: int(x.replace("p", "")), reverse=True)
        if not sorted_qualities:
            sorted_qualities = ["720p", "480p", "360p"]

        return {
            "url": valid_url,
            "title": info.get("title", "بدون عنوان"),
            "duration": duration,
            "duration_formatted": cls._format_seconds(duration),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "نامشخص"),
            "available_qualities": sorted_qualities
        }

    @classmethod
    async def download_video(cls, url: str, output_path: Path) -> Path:
        valid_url = validate_youtube_url(url)
        output_template = str(output_path.with_suffix('')) + ".%(ext)s"
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best[height<=720]',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'overwrites': True
        }
        
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([valid_url])
            )
        except Exception as e:
            logger.error(f"Error downloading video {url}: {str(e)}")
            raise RuntimeError(f"خطا در دانلود ویدیو: {str(e)}")

        expected_file = output_path.with_suffix('.mp4')
        if not expected_file.exists():
            # Search for any matched output file
            matches = list(output_path.parent.glob(f"{output_path.stem}.*"))
            if matches:
                return matches[0]
            raise FileNotFoundError("فایل ویدیوی دانلود شده یافت نشد.")
        return expected_file