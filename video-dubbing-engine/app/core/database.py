import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.core.config import settings

async def init_db():
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                duration REAL,
                thumbnail TEXT,
                source_language TEXT,
                target_language TEXT,
                voice_id TEXT,
                keep_original_audio INTEGER DEFAULT 0,
                original_audio_volume REAL DEFAULT 0.2,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                current_step TEXT,
                error_message TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await db.commit()

async def create_job_record(job_dict: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO jobs (
                id, url, title, duration, thumbnail, source_language,
                target_language, voice_id, keep_original_audio,
                original_audio_volume, status, progress, current_step,
                error_message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_dict["id"], job_dict["url"], job_dict.get("title", ""),
            job_dict.get("duration", 0.0), job_dict.get("thumbnail", ""),
            job_dict.get("source_language", "auto"), job_dict.get("target_language", "fa"),
            job_dict.get("voice_id", ""), 1 if job_dict.get("keep_original_audio") else 0,
            job_dict.get("original_audio_volume", 0.2), job_dict.get("status", "queued"),
            job_dict.get("progress", 0.0), job_dict.get("current_step", "در صف پردازش"),
            job_dict.get("error_message", None), now, now
        ))
        await db.commit()

async def update_job_record(job_id: str, updates: Dict[str, Any]) -> None:
    updates["updated_at"] = datetime.utcnow().isoformat()
    keys = list(updates.keys())
    set_clause = ", ".join([f"{k} = ?" for k in keys])
    values = [updates[k] for k in keys]
    values.append(job_id)
    
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
        await db.commit()

async def get_job_record(job_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["keep_original_audio"] = bool(d["keep_original_audio"])
                return d
            return None

async def list_jobs_records(limit: int = 20) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["keep_original_audio"] = bool(d["keep_original_audio"])
                result.append(d)
            return result