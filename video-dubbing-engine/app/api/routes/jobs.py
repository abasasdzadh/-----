import uuid
import json
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from app.models.job import JobCreateRequest, JobResponse
from app.core.config import settings, get_effective_gemini_key
from app.core.database import create_job_record, get_job_record, list_jobs_records, update_job_record
from app.core.security import validate_youtube_url, safe_join_path
from app.workers.job_manager import JobManager
from app.api.deps import get_job_manager
from app.services.youtube import YouTubeService

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobResponse)
async def create_job(request: JobCreateRequest, manager: JobManager = Depends(get_job_manager)):
    if not get_effective_gemini_key():
        raise HTTPException(
            status_code=400,
            detail="کلید Gemini API Key تنظیم نشده است. لطفاً ابتدا در بخش تنظیمات کلید را وارد نمایید."
        )

    valid_url = validate_youtube_url(request.url)
    
    # Extract metadata beforehand
    try:
        meta = await YouTubeService.inspect_video(valid_url)
    except Exception as e:
        meta = {"title": "YouTube Video", "duration": 0.0, "thumbnail": ""}

    job_id = uuid.uuid4().hex[:10]
    job_dict = {
        "id": job_id,
        "url": valid_url,
        "title": meta.get("title", "بدون عنوان"),
        "duration": meta.get("duration", 0.0),
        "thumbnail": meta.get("thumbnail", ""),
        "source_language": request.source_language,
        "target_language": request.target_language,
        "voice_id": request.voice_id,
        "keep_original_audio": request.keep_original_audio,
        "original_audio_volume": request.original_audio_volume,
        "status": "queued",
        "progress": 0.0,
        "current_step": "در صف پردازش",
        "error_message": None
    }
    
    await create_job_record(job_dict)
    await manager.submit_job(job_dict)
    
    created = await get_job_record(job_id)
    return JobResponse(job_id=job_id, **created)

@router.get("", response_model=list[JobResponse])
async def list_jobs():
    rows = await list_jobs_records(limit=20)
    return [JobResponse(job_id=r["id"], **r) for r in rows]

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job = await get_job_record(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="عملیات موردنظر یافت نشد.")
    return JobResponse(job_id=job["id"], **job)

@router.get("/{job_id}/events")
async def stream_job_events(job_id: str, manager: JobManager = Depends(get_job_manager)):
    job = await get_job_record(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="عملیات موردنظر یافت نشد.")

    async def event_generator():
        queue = await manager.subscribe(job_id)
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                if data.get("status") in ["completed", "failed", "cancelled"]:
                    break
        finally:
            manager.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, manager: JobManager = Depends(get_job_manager)):
    success = await manager.cancel_job(job_id)
    return {"status": "cancelled" if success else "not_running"}

@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: str, manager: JobManager = Depends(get_job_manager)):
    job = await get_job_record(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="عملیات موردنظر یافت نشد.")
    
    await update_job_record(job_id, {
        "status": "queued",
        "progress": 0.0,
        "current_step": "آماده‌سازی برای شروع مجدد...",
        "error_message": None
    })
    
    await manager.submit_job(job)
    updated = await get_job_record(job_id)
    return JobResponse(job_id=job_id, **updated)

@router.get("/{job_id}/video")
async def download_video(job_id: str):
    video_path = safe_join_path(settings.JOBS_DIR, job_id, "output", "dubbed_final.mp4")
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="فایل ویدیوی خروجی هنوز آماده نشده است.")
    return FileResponse(
        str(video_path), 
        media_type="video/mp4", 
        filename=f"dubbed_{job_id}.mp4"
    )

@router.get("/{job_id}/transcript")
async def get_transcript(job_id: str):
    path = safe_join_path(settings.JOBS_DIR, job_id, "transcript", "transcription.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="متن استخراج‌شده هنوز آماده نشده است.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/{job_id}/translation")
async def get_translation(job_id: str):
    path = safe_join_path(settings.JOBS_DIR, job_id, "translation", "translation.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="ترجمه هنوز آماده نشده است.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)