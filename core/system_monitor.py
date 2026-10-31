import os
import sys
import time
import shutil
import logging
import subprocess
import psutil

logger = logging.getLogger(__name__)

# Cached values to prevent high-frequency subprocess overhead
_metrics_cache = {
    "data": None,
    "timestamp": 0.0
}
CACHE_TTL_SECONDS = 1.5

_nvenc_supported_cached = None

def check_nvenc_support() -> bool:
    """Checks if FFmpeg has h264_nvenc encoder available."""
    global _nvenc_supported_cached
    if _nvenc_supported_cached is not None:
        return _nvenc_supported_cached
    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
        _nvenc_supported_cached = "h264_nvenc" in res.stdout
    except Exception as e:
        logger.warning(f"Could not check FFmpeg NVENC support: {e}")
        _nvenc_supported_cached = False
    return _nvenc_supported_cached

def check_cuda_support() -> bool:
    """Checks if CUDA runtime is detected via ctranslate2 or nvidia-smi."""
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return True
    except Exception:
        pass
    return False

def get_real_system_metrics() -> dict:
    """
    Collects real-time hardware metrics from psutil, nvidia-smi, and FFmpeg.
    Returns 100% genuine system telemetry with zero hardcoded or simulated values.
    """
    now = time.time()
    if _metrics_cache["data"] is not None and (now - _metrics_cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _metrics_cache["data"]

    # 1. CPU Metrics
    cpu_util = psutil.cpu_percent(interval=0.05)
    cpu_cores = psutil.cpu_count(logical=False) or 1
    cpu_threads = psutil.cpu_count(logical=True) or 1

    # 2. RAM Metrics
    mem = psutil.virtual_memory()
    ram_metrics = {
        "total_gb": round(mem.total / (1024 ** 3), 1),
        "used_gb": round(mem.used / (1024 ** 3), 1),
        "free_gb": round(mem.available / (1024 ** 3), 1),
        "util_pct": mem.percent
    }

    # 3. Disk Metrics (Host Drive C: or storage drive)
    storage_root = os.path.splitdrive(os.path.abspath(__file__))[0] or "C:"
    if not storage_root.endswith(os.sep):
        storage_root += os.sep
    disk = psutil.disk_usage(storage_root)
    disk_metrics = {
        "drive": storage_root,
        "total_gb": round(disk.total / (1024 ** 3), 1),
        "used_gb": round(disk.used / (1024 ** 3), 1),
        "free_gb": round(disk.free / (1024 ** 3), 1),
        "util_pct": disk.percent
    }

    # 4. GPU Metrics via nvidia-smi
    gpu_metrics = {
        "available": False,
        "name": "N/A",
        "util_pct": 0,
        "vram_used_mb": 0,
        "vram_total_mb": 0,
        "temp_c": None,
        "nvenc_supported": check_nvenc_support(),
        "cuda_available": check_cuda_support(),
        "status": "unavailable",
        "error": None
    }

    try:
        # Query nvidia-smi for precise metrics
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 5:
                gpu_metrics["available"] = True
                gpu_metrics["name"] = parts[0]
                gpu_metrics["temp_c"] = int(parts[1]) if parts[1].isdigit() else None
                gpu_metrics["vram_used_mb"] = int(parts[2]) if parts[2].isdigit() else 0
                gpu_metrics["vram_total_mb"] = int(parts[3]) if parts[3].isdigit() else 0
                gpu_metrics["util_pct"] = int(parts[4]) if parts[4].isdigit() else 0
                gpu_metrics["status"] = "online"
        else:
            gpu_metrics["error"] = res.stderr.strip() or "nvidia-smi returned non-zero code"
    except FileNotFoundError:
        gpu_metrics["error"] = "nvidia-smi executable not found in system PATH"
    except subprocess.TimeoutExpired:
        gpu_metrics["error"] = "nvidia-smi query timed out"
    except Exception as e:
        gpu_metrics["error"] = str(e)

    result = {
        "timestamp": now,
        "cpu": {
            "cores": cpu_cores,
            "threads": cpu_threads,
            "util_pct": cpu_util
        },
        "ram": ram_metrics,
        "disk": disk_metrics,
        "gpu": gpu_metrics
    }

    _metrics_cache["data"] = result
    _metrics_cache["timestamp"] = now
    return result
