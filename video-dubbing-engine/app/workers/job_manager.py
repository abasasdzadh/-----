import asyncio
from typing import Dict, Set
from app.core.config import settings
from app.core.database import update_job_record, get_job_record
from app.services.dubbing_pipeline import DubbingPipeline
from app.utils.logger import logger

class JobManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
            cls._instance.active_tasks: Dict[str, asyncio.Task] = {}
            cls._instance.subscribers: Dict[str, Set[asyncio.Queue]] = {}
            cls._instance.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)
        return cls._instance

    async def submit_job(self, job_dict: dict):
        job_id = job_dict["id"]
        task = asyncio.create_task(self._run_job_wrapper(job_dict))
        self.active_tasks[job_id] = task

    async def _run_job_wrapper(self, job_dict: dict):
        job_id = job_dict["id"]
        async with self.semaphore:
            async def progress_callback(status: str, progress: float, step_desc: str):
                await self.broadcast_event(job_id, {
                    "job_id": job_id,
                    "status": status,
                    "progress": progress,
                    "current_step": step_desc,
                    "error_message": step_desc if status == "failed" else None
                })
                updates = {
                    "status": status,
                    "progress": progress,
                    "current_step": step_desc
                }
                if status == "failed":
                    updates["error_message"] = step_desc
                await update_job_record(job_id, updates)

            pipeline = DubbingPipeline(job_dict, progress_callback)
            try:
                await pipeline.execute()
            except Exception as e:
                logger.error(f"JobManager: Task {job_id} encountered exception: {e}")
            finally:
                if job_id in self.active_tasks:
                    del self.active_tasks[job_id]

    async def cancel_job(self, job_id: str) -> bool:
        task = self.active_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            await update_job_record(job_id, {
                "status": "cancelled",
                "current_step": "عملیات لغو شد."
            })
            await self.broadcast_event(job_id, {
                "job_id": job_id,
                "status": "cancelled",
                "progress": 0.0,
                "current_step": "عملیات لغو شد."
            })
            return True
        return False

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        if job_id not in self.subscribers:
            self.subscribers[job_id] = set()
        queue = asyncio.Queue()
        self.subscribers[job_id].add(queue)
        
        # Send initial status
        job_data = await get_job_record(job_id)
        if job_data:
            await queue.put({
                "job_id": job_id,
                "status": job_data["status"],
                "progress": job_data["progress"],
                "current_step": job_data["current_step"],
                "error_message": job_data.get("error_message")
            })
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        if job_id in self.subscribers:
            self.subscribers[job_id].discard(queue)
            if not self.subscribers[job_id]:
                del self.subscribers[job_id]

    async def broadcast_event(self, job_id: str, event_data: dict):
        if job_id in self.subscribers:
            for q in list(self.subscribers[job_id]):
                await q.put(event_data)

job_manager = JobManager()