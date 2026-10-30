import os
import sys
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from core.audio import (
    get_video_info,
    extract_preview_frame,
    extract_timeline_thumbnails,
    download_youtube_video,
    trim_video,
    extract_audio
)
from core.transcriber import AudioTranscriber
from core.highlight_detector import HighlightDetector
from pipeline import ShortsPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AutoShorts Studio API", version="2.0.0")

# Enable CORS for Vite React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "outputs")
CACHE_DIR = os.path.join(STORAGE_DIR, "cache")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")

for d in [UPLOAD_DIR, OUTPUTS_DIR, CACHE_DIR, AUDIO_DIR]:
    os.makedirs(d, exist_ok=True)

# Mount Static Storage
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# Global In-Memory Session State
session_state: Dict[str, Any] = {
    "video_path": None,
    "video_meta": {"width": 1920, "height": 1080, "duration": 0.0, "fps": 30.0},
    "preview_frame": None,
    "timeline_thumbs": [],
    "discovered_clips": [],
    "render_job": {"status": "idle", "progress": 0, "message": "", "results": []}
}

# Auto-load latest uploaded video if available
existing_vids = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")) and not f.endswith(".part")]
if existing_vids:
    latest_vid = os.path.join(UPLOAD_DIR, existing_vids[0])
    try:
        session_state["video_path"] = latest_vid
        meta = get_video_info(latest_vid)
        session_state["video_meta"] = meta
        v_base = os.path.splitext(existing_vids[0])[0]
        p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
        extract_preview_frame(latest_vid, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
        session_state["preview_frame"] = p_frame
        session_state["timeline_thumbs"] = extract_timeline_thumbnails(latest_vid, CACHE_DIR, meta["duration"], count=6)
    except Exception as e:
        logger.warning(f"Could not auto-load initial video: {e}")


# -------------------------------------------------------------
# PYDANTIC SCHEMAS
# -------------------------------------------------------------
class YouTubeImportRequest(BaseModel):
    url: str

class SelectVideoRequest(BaseModel):
    filename: str

class TrimVideoRequest(BaseModel):
    start_time: float
    end_time: float

class ScanHighlightsRequest(BaseModel):
    num_clips: int = 3
    min_duration: int = 20
    max_duration: int = 50
    scan_start: float = 0.0

class RenderRequest(BaseModel):
    clips: List[Dict[str, Any]]
    layout_mode: str = "gaming_split"  # gaming_split | crop | blur_fit
    gaming_config: Optional[Dict[str, Any]] = None
    single_crop_config: Optional[Dict[str, Any]] = None
    subtitle_theme: str = "Hormozi Gold (Viral)"
    enable_emojis: bool = True


# -------------------------------------------------------------
# API ROUTES
# -------------------------------------------------------------
@app.get("/api/health")
def get_health():
    return {
        "status": "online",
        "gpu": "NVIDIA GeForce RTX 3050 (NVENC 60fps Active)",
        "cuda": "CUDA 12 float16",
        "models": {
            "stt": "faster-whisper (small)",
            "llm": "ollama (llama3.2:latest)"
        }
    }

@app.get("/api/session")
def get_session():
    v_path = session_state.get("video_path")
    v_url = None
    p_url = None
    thumbs_urls = []

    if v_path and os.path.exists(v_path):
        rel_v = os.path.relpath(v_path, STORAGE_DIR).replace("\\", "/")
        v_url = f"/storage/{rel_v}"

    p_frame = session_state.get("preview_frame")
    if p_frame and os.path.exists(p_frame):
        rel_p = os.path.relpath(p_frame, STORAGE_DIR).replace("\\", "/")
        p_url = f"/storage/{rel_p}"

    for t in session_state.get("timeline_thumbs", []):
        if os.path.exists(t["path"]):
            rel_t = os.path.relpath(t["path"], STORAGE_DIR).replace("\\", "/")
            thumbs_urls.append({"timestamp": t["timestamp"], "url": f"/storage/{rel_t}"})

    return {
        "video_path": v_path,
        "video_url": v_url,
        "filename": os.path.basename(v_path) if v_path else None,
        "meta": session_state.get("video_meta"),
        "preview_url": p_url,
        "timeline_thumbs": thumbs_urls,
        "discovered_clips": session_state.get("discovered_clips", []),
        "render_job": session_state.get("render_job")
    }

@app.get("/api/sessions/local")
def get_local_sessions():
    vids = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")) and not f.endswith(".part")]
    res = []
    for f in vids:
        fp = os.path.join(UPLOAD_DIR, f)
        res.append({
            "filename": f,
            "size_mb": round(os.path.getsize(fp) / (1024 * 1024), 1)
        })
    return res

@app.post("/api/sessions/select")
def select_local_session(req: SelectVideoRequest):
    target = os.path.join(UPLOAD_DIR, req.filename)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="File not found")

    meta = get_video_info(target)
    session_state["video_path"] = target
    session_state["video_meta"] = meta
    v_base = os.path.splitext(req.filename)[0]
    p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
    extract_preview_frame(target, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
    session_state["preview_frame"] = p_frame
    session_state["timeline_thumbs"] = extract_timeline_thumbnails(target, CACHE_DIR, meta["duration"], count=6)
    session_state["discovered_clips"] = []
    return get_session()

@app.post("/api/import/youtube")
def import_youtube(req: YouTubeImportRequest):
    if not req.url or "http" not in req.url:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        downloaded = download_youtube_video(req.url, UPLOAD_DIR)
        meta = get_video_info(downloaded)
        session_state["video_path"] = downloaded
        session_state["video_meta"] = meta
        v_base = os.path.splitext(os.path.basename(downloaded))[0]
        p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
        extract_preview_frame(downloaded, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
        session_state["preview_frame"] = p_frame
        session_state["timeline_thumbs"] = extract_timeline_thumbnails(downloaded, CACHE_DIR, meta["duration"], count=6)
        session_state["discovered_clips"] = []
        return get_session()
    except Exception as e:
        logger.error(f"YouTube import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/import/upload")
async def import_upload(file: UploadFile = File(...)):
    target_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(target_path, "wb") as f:
        content = await file.read()
        f.write(content)

    meta = get_video_info(target_path)
    session_state["video_path"] = target_path
    session_state["video_meta"] = meta
    v_base = os.path.splitext(file.filename)[0]
    p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
    extract_preview_frame(target_path, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
    session_state["preview_frame"] = p_frame
    session_state["timeline_thumbs"] = extract_timeline_thumbnails(target_path, CACHE_DIR, meta["duration"], count=6)
    session_state["discovered_clips"] = []
    return get_session()

@app.get("/api/frame")
def get_frame_at_timestamp(timestamp: float = 0.0):
    v_path = session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video")

    v_base = os.path.splitext(os.path.basename(v_path))[0]
    out_jpg = os.path.join(CACHE_DIR, f"{v_base}_frame_{int(timestamp)}s.jpg")
    extract_preview_frame(v_path, out_jpg, timestamp=timestamp)

    rel_p = os.path.relpath(out_jpg, STORAGE_DIR).replace("\\", "/")
    return {"timestamp": timestamp, "url": f"/storage/{rel_p}"}

@app.post("/api/video/trim")
def trim_current_video(req: TrimVideoRequest):
    v_path = session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video to trim")

    v_base = os.path.splitext(os.path.basename(v_path))[0]
    trimmed_name = f"{v_base}_trim_{int(req.start_time)}s.mp4"
    trimmed_path = os.path.join(UPLOAD_DIR, trimmed_name)

    trim_video(v_path, trimmed_path, req.start_time, req.end_time)

    if not os.path.exists(trimmed_path):
        raise HTTPException(status_code=500, detail="Trim operation failed")

    meta = get_video_info(trimmed_path)
    session_state["video_path"] = trimmed_path
    session_state["video_meta"] = meta
    p_frame = os.path.join(CACHE_DIR, f"{os.path.splitext(trimmed_name)[0]}_preview.jpg")
    extract_preview_frame(trimmed_path, p_frame, timestamp=min(5.0, meta["duration"] * 0.2))
    session_state["preview_frame"] = p_frame
    session_state["timeline_thumbs"] = extract_timeline_thumbnails(trimmed_path, CACHE_DIR, meta["duration"], count=6)
    session_state["discovered_clips"] = []
    return get_session()

@app.post("/api/highlights/scan")
def scan_highlights(req: ScanHighlightsRequest):
    v_path = session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video")

    try:
        p = ShortsPipeline()
        v_base = os.path.splitext(os.path.basename(v_path))[0]
        audio_file = os.path.join(AUDIO_DIR, f"{v_base}.wav")
        if not os.path.exists(audio_file):
            extract_audio(v_path, audio_file)

        cache_file = os.path.join(CACHE_DIR, f"{v_base}_transcript.json")
        t_data = AudioTranscriber.load_cache(cache_file)
        if not t_data:
            p.transcriber = AudioTranscriber(model_size=p.whisper_model_name)
            t_data = p.transcriber.transcribe(audio_file)
            AudioTranscriber.save_cache(t_data, cache_file)

        h_detector = HighlightDetector(model_name=p.ollama_model_name)
        clips = h_detector.find_highlights(
            t_data,
            num_clips=req.num_clips,
            min_duration=req.min_duration,
            max_duration=req.max_duration,
            scan_start=req.scan_start
        )

        session_state["discovered_clips"] = clips
        return {"clips": clips}
    except Exception as e:
        logger.error(f"Highlight scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_render_task(req: RenderRequest):
    v_path = session_state.get("video_path")
    if not v_path:
        session_state["render_job"] = {"status": "error", "progress": 0, "message": "No video"}
        return

    try:
        session_state["render_job"] = {"status": "running", "progress": 5, "message": "Starting GPU render...", "results": []}

        def on_prog(title, pct, msg):
            session_state["render_job"]["progress"] = int(pct)
            session_state["render_job"]["message"] = f"{title}: {msg}"

        pipeline = ShortsPipeline()
        results = pipeline.process(
            video_source=v_path,
            is_youtube=False,
            num_clips=len(req.clips),
            subtitle_theme=req.subtitle_theme,
            enable_emojis=req.enable_emojis,
            layout_mode=req.layout_mode,
            gaming_config=req.gaming_config,
            single_crop_config=req.single_crop_config,
            preselected_clips=req.clips,
            progress_callback=on_prog
        )

        # Enrich results with urls
        for r in results:
            rel_vp = os.path.relpath(r["video_path"], STORAGE_DIR).replace("\\", "/")
            r["video_url"] = f"/storage/{rel_vp}"

        session_state["render_job"] = {
            "status": "complete",
            "progress": 100,
            "message": "Render completed successfully!",
            "results": results
        }
    except Exception as e:
        logger.error(f"Render failed: {e}")
        session_state["render_job"] = {
            "status": "error",
            "progress": 0,
            "message": f"Render failed: {str(e)}",
            "results": []
        }

@app.post("/api/render")
def trigger_render(req: RenderRequest, bg_tasks: BackgroundTasks):
    v_path = session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video")
    if not req.clips:
        raise HTTPException(status_code=400, detail="No clips specified to render")

    bg_tasks.add_task(run_render_task, req)
    return {"status": "started", "message": f"Rendering {len(req.clips)} clips in background..."}

@app.get("/api/render/status")
def get_render_status():
    return session_state.get("render_job", {"status": "idle"})

@app.get("/api/library")
def get_library():
    shorts = [f for f in os.listdir(OUTPUTS_DIR) if f.lower().endswith(".mp4") and not f.startswith(".")]
    res = []
    for s in shorts:
        fp = os.path.join(OUTPUTS_DIR, s)
        rel_sp = os.path.relpath(fp, STORAGE_DIR).replace("\\", "/")
        res.append({
            "filename": s,
            "size_mb": round(os.path.getsize(fp) / (1024 * 1024), 1),
            "video_url": f"/storage/{rel_sp}"
        })
    return res

# Mount built React Frontend (Production / Desktop Mode)
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
