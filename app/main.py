from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.core.config import settings
from app.core.database import init_db
from app.core.hardware import get_system_hardware_info
from app.api.routes import video, jobs, settings as settings_route
from app.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Automated Video Dubbing Engine...")
    await init_db()
    hw = get_system_hardware_info()
    logger.info(
        f"Hardware detected: CPU Cores={hw['cpu_cores']} | RAM={hw['total_ram_gb']}GB | "
        f"CUDA={hw['cuda_available']} | FFmpeg Installed={hw['ffmpeg_installed']}"
    )
    yield
    logger.info("Shutting down Dubbing Engine...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(video.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(settings_route.router, prefix="/api")

# Static frontend assets
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")