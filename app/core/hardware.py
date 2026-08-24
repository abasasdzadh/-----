import shutil
import psutil
from typing import Dict, Any

def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def get_system_hardware_info() -> Dict[str, Any]:
    cpu_count = psutil.cpu_count(logical=True)
    cpu_percent = psutil.cpu_percent(interval=None)
    virtual_mem = psutil.virtual_memory()
    total_ram_gb = round(virtual_mem.total / (1024 ** 3), 2)
    available_ram_gb = round(virtual_mem.available / (1024 ** 3), 2)
    
    cuda_available = False
    gpu_name = None
    try:
        import torch
        if torch.cuda.is_available():
            cuda_available = True
            gpu_name = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    
    # Intelligent model recommendation for Whisper
    if cuda_available:
        recommended_model = "small" if total_ram_gb < 8 else "medium"
        device = "cuda"
        compute_type = "float16"
    else:
        device = "cpu"
        compute_type = "int8"
        if total_ram_gb < 4:
            recommended_model = "tiny"
        elif total_ram_gb < 8:
            recommended_model = "base"
        else:
            recommended_model = "small"
            
    return {
        "cpu_cores": cpu_count,
        "cpu_usage_percent": cpu_percent,
        "total_ram_gb": total_ram_gb,
        "available_ram_gb": available_ram_gb,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "ffmpeg_installed": check_ffmpeg(),
        "recommended_whisper_model": recommended_model,
        "recommended_device": device,
        "recommended_compute_type": compute_type
    }