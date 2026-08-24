import re
from pathlib import Path
from fastapi import HTTPException

YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)([\w-]{11})([?&].*)?$'
)

def validate_youtube_url(url: str) -> str:
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="آدرس ویدیو نمی‌تواند خالی باشد.")
    url = url.strip()
    match = YOUTUBE_URL_REGEX.match(url)
    if not match:
        raise HTTPException(
            status_code=400, 
            detail="آدرس وارد شده یک آدرس معتبر یوتیوب نیست."
        )
    return url

def sanitize_filename(name: str) -> str:
    # Keep only alphanumeric, underscores, hyphens, and periods
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    return clean[:100]

def safe_join_path(base_dir: Path, *paths: str) -> Path:
    target = (base_dir / Path(*paths)).resolve()
    if not str(target).startswith(str(base_dir.resolve())):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز به مسیر فایل.")
    return target

def mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"