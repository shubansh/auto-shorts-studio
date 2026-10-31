import os
import sys
import re
import json
import time
import uuid
import shutil
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure UTF-8 output and stable asyncio loop on Windows
if sys.platform == "win32":
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
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
    extract_audio,
    generate_audio_waveform
)
from core.transcriber import AudioTranscriber
from core.highlight_detector import HighlightDetector
from core.system_monitor import get_real_system_metrics
from core.database import (
    init_db,
    migrate_existing_uploads_to_projects,
    get_all_projects,
    get_project_by_id,
    save_project,
    delete_project_metadata,
    get_all_settings,
    set_setting,
    get_db,
    create_default_project_state,
    utc_now_iso,
    DB_PATH
)
from pipeline import ShortsPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ClipForge API", version="2.1.0")

# -------------------------------------------------------------
# SECURITY: RESTRICTED LOCAL-FIRST CORS
# -------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

# Mount Static Storage strictly for media asset serving
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# -------------------------------------------------------------
# SECURITY: PATH SANITIZATION & URL VALIDATION HELPERS
# -------------------------------------------------------------
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB limit

def sanitize_filename(filename: str) -> str:
    """Removes any path traversal attempts and replaces dangerous characters."""
    if not filename:
        raise HTTPException(status_code=400, detail="Empty filename provided")
    base = os.path.basename(filename.strip().replace("\\", "/"))
    clean = re.sub(r'[^a-zA-Z0-9_\.\-]', '_', base)
    while clean.startswith("."):
        clean = clean[1:]
    if not clean:
        clean = f"media_{int(time.time())}.mp4"
    return clean

def get_safe_storage_path(filename: str, base_dir: str = UPLOAD_DIR) -> str:
    """Resolves filename and strictly ensures it stays within the permitted base_dir."""
    clean_name = sanitize_filename(filename)
    base_abs = os.path.abspath(base_dir)
    resolved_path = os.path.abspath(os.path.join(base_abs, clean_name))
    if not resolved_path.startswith(base_abs + os.sep) and resolved_path != base_abs:
        logger.warning(f"Security Alert: Directory traversal attempt blocked: {filename}")
        raise HTTPException(status_code=400, detail="Invalid path: directory traversal rejected")
    return resolved_path

def validate_remote_url(url: str) -> str:
    """Validates remote video URL and prevents SSRF attacks."""
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs are allowed")
    
    hostname = (parsed.hostname or "").lower()
    blocked_hosts = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.", "10.", "192.168.", "172.16.")
    for bh in blocked_hosts:
        if hostname == bh or hostname.startswith(bh):
            raise HTTPException(status_code=400, detail="Requests to local or private network addresses are prohibited")
    
    allowed_domains = ("youtube.com", "youtu.be", "twitch.tv")
    if not any(hostname == ad or hostname.endswith("." + ad) for ad in allowed_domains):
        raise HTTPException(status_code=400, detail="Supported video providers are YouTube (youtube.com, youtu.be) and Twitch (twitch.tv)")
    return url


# -------------------------------------------------------------
# DATABASE PERSISTENCE INITIALIZATION
# -------------------------------------------------------------
try:
    init_db()
    migrated_count = migrate_existing_uploads_to_projects()
    if migrated_count > 0:
        logger.info(f"Successfully migrated {migrated_count} legacy media files to SQLite projects.")
except Exception as e:
    logger.error(f"Failed to initialize SQLite database: {e}")

# -------------------------------------------------------------
# GLOBAL IN-MEMORY SESSION STATE (BACKED BY SQLITE)
# -------------------------------------------------------------
session_state: Dict[str, Any] = {
    "active_project_id": None,
    "video_path": None,
    "video_meta": {"width": 1920, "height": 1080, "duration": 0.0, "fps": 30.0},
    "preview_frame": None,
    "timeline_thumbs": [],
    "discovered_clips": [],
    "render_job": {"status": "idle", "progress": 0, "message": "", "results": []}
}

# Auto-load latest project / video if available
existing_vids = [
    f for f in os.listdir(UPLOAD_DIR)
    if os.path.splitext(f)[1].lower() in ALLOWED_VIDEO_EXTENSIONS and not f.endswith(".part")
]
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
        
        # Link to corresponding SQLite project if present
        all_projs = get_all_projects()
        for p in all_projs:
            if p.get("media_filename") == existing_vids[0]:
                session_state["active_project_id"] = p["id"]
                break
    except Exception as e:
        logger.warning(f"Could not auto-load initial video: {e}")


# -------------------------------------------------------------
# PYDANTIC SCHEMAS
# -------------------------------------------------------------
class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""
    media_filename: Optional[str] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    project_state: Optional[Dict[str, Any]] = None

class UpdateSettingsRequest(BaseModel):
    settings: Dict[str, Any]

class YouTubeImportRequest(BaseModel):
    url: str

class SelectVideoRequest(BaseModel):
    filename: str

class TrimVideoRequest(BaseModel):
    video_path: Optional[str] = Field(None, description="Optional path to video file to trim. Defaults to active session.")
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., gt=0.0)
    mode: str = Field("fast", description="fast (keyframe stream copy) or accurate (NVENC/CPU re-encode)")

class ScanHighlightsRequest(BaseModel):
    num_clips: int = Field(3, ge=1, le=10)
    min_duration: int = Field(20, ge=10, le=120)
    max_duration: int = Field(50, ge=15, le=180)
    scan_start: float = Field(0.0, ge=0.0)

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
    """Health check endpoint with local engine status."""
    return {
        "status": "online",
        "service": "ClipForge Local Studio",
        "version": "2.1.0",
        "models": {
            "stt": "faster-whisper (CUDA 12 FP16)",
            "llm": "ollama (llama3.2:latest)"
        }
    }

@app.get("/api/system/metrics")
async def get_system_metrics():
    """
    Returns 100% genuine real-time system hardware telemetry.
    Queries psutil, nvidia-smi, and FFmpeg without any hardcoded values.
    """
    return get_real_system_metrics()

@app.get("/api/session")
def get_session():
    """Returns active editing session metadata, thumbnails, preview URLs, and SQLite project ID."""
    v_path = session_state.get("video_path")
    
    # Auto-resolve active_project_id from SQLite database if missing or out-of-sync
    curr_proj_id = session_state.get("active_project_id")
    if curr_proj_id:
        if not get_project_by_id(curr_proj_id):
            curr_proj_id = None
            session_state["active_project_id"] = None

    if not curr_proj_id and v_path and os.path.exists(v_path):
        fn = os.path.basename(v_path)
        all_projs = get_all_projects()
        for p in all_projs:
            if p.get("media_filename") == fn:
                session_state["active_project_id"] = p["id"]
                curr_proj_id = p["id"]
                break
        if not curr_proj_id:
            migrate_existing_uploads_to_projects()
            for p in get_all_projects():
                if p.get("media_filename") == fn:
                    session_state["active_project_id"] = p["id"]
                    curr_proj_id = p["id"]
                    break

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
        "active_project_id": session_state.get("active_project_id"),
        "video_path": v_path,
        "video_url": v_url,
        "filename": os.path.basename(v_path) if v_path else None,
        "meta": session_state.get("video_meta"),
        "preview_url": p_url,
        "timeline_thumbs": thumbs_urls,
        "discovered_clips": session_state.get("discovered_clips", []),
        "render_job": session_state.get("render_job")
    }

# -------------------------------------------------------------
# PERSISTENT PROJECTS API (SQLITE BACKED)
# -------------------------------------------------------------

@app.get("/api/projects")
def list_projects():
    """Returns all projects stored in SQLite ordered by updated_at descending."""
    return get_all_projects()

@app.post("/api/projects")
def create_project(req: CreateProjectRequest):
    """Creates a new persistent project with non-destructive initial state."""
    name_clean = req.name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
        
    project_id = str(uuid.uuid4())
    now_iso = utc_now_iso()
    
    media_info = None
    media_id = None
    target_path = None
    
    if req.media_filename:
        target_path = get_safe_storage_path(req.media_filename, UPLOAD_DIR)
        if not os.path.exists(target_path):
            raise HTTPException(status_code=404, detail="Referenced media file does not exist in uploads")
        try:
            media_info = get_video_info(target_path)
            media_info["filename"] = os.path.basename(target_path)
        except Exception as e:
            logger.warning(f"Failed to probe media for new project: {e}")
            media_info = {"width": 1920, "height": 1080, "duration": 60.0, "fps": 30.0, "filename": req.media_filename}
            
    proj_state = create_default_project_state(media_info)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, name_clean, req.description or "", json.dumps(proj_state), now_iso, now_iso))
        
        if req.media_filename and target_path and os.path.exists(target_path):
            media_id = str(uuid.uuid4())
            cursor.execute("""
            INSERT INTO media_assets (
                id, project_id, original_path, filename, duration, width, height, fps, codec, audio_available, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                media_id,
                project_id,
                target_path,
                os.path.basename(target_path),
                media_info.get("duration", 0.0),
                media_info.get("width", 1920),
                media_info.get("height", 1080),
                media_info.get("fps", 30.0),
                "h264",
                1,
                now_iso
            ))
            
    session_state["active_project_id"] = project_id
    if target_path and os.path.exists(target_path):
        session_state["video_path"] = target_path
        session_state["video_meta"] = media_info
    return get_project_by_id(project_id)

@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    """Retrieves full project details including media asset, clips, and render history."""
    proj = get_project_by_id(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.put("/api/projects/{project_id}")
def update_project(project_id: str, req: UpdateProjectRequest):
    """
    Non-destructively updates project metadata and project_state JSON.
    Guarantees original source media remains untouched.
    """
    existing = get_project_by_id(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_name = req.name.strip() if req.name is not None else existing["name"]
    if not new_name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
    new_desc = req.description if req.description is not None else existing.get("description", "")
    new_state = req.project_state if req.project_state is not None else existing.get("project_state", {})
    
    # Validate JSON serializability
    try:
        json.dumps(new_state)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid project_state: {e}")
        
    updated = save_project(project_id, new_name, new_state, new_desc)
    return updated

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str, delete_media: bool = False):
    """
    Deletes project metadata from SQLite.
    Original source video is PRESERVED by default (delete_media=False).
    """
    existing = get_project_by_id(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    
    success = delete_project_metadata(project_id, delete_media_files=delete_media)
    if session_state.get("active_project_id") == project_id:
        session_state["active_project_id"] = None
        
    return {
        "status": "deleted",
        "project_id": project_id,
        "media_deleted": delete_media
    }

# -------------------------------------------------------------
# SYSTEM SETTINGS API (SQLITE PERSISTED)
# -------------------------------------------------------------

@app.get("/api/settings")
def get_system_settings_route():
    """Returns persisted user and hardware preferences from SQLite."""
    return get_all_settings()

@app.post("/api/settings")
def update_system_settings_route(req: UpdateSettingsRequest):
    """Updates one or more system settings in SQLite."""
    for k, v in req.settings.items():
        set_setting(k, v)
    return get_all_settings()

@app.get("/api/sessions/local")
def get_local_sessions():
    """Returns list of local video files stored in the uploads directory."""
    vids = [
        f for f in os.listdir(UPLOAD_DIR)
        if os.path.splitext(f)[1].lower() in ALLOWED_VIDEO_EXTENSIONS and not f.endswith(".part")
    ]
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
    """Safely selects an uploaded video and sets it as the active editing project."""
    target = get_safe_storage_path(req.filename, UPLOAD_DIR)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Requested video file does not exist")

    meta = get_video_info(target)
    session_state["video_path"] = target
    session_state["video_meta"] = meta
    v_base = os.path.splitext(os.path.basename(target))[0]
    p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
    extract_preview_frame(target, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
    session_state["preview_frame"] = p_frame
    session_state["timeline_thumbs"] = extract_timeline_thumbnails(target, CACHE_DIR, meta["duration"], count=6)
    session_state["discovered_clips"] = []

    # Find or link corresponding SQLite project
    matched_id = None
    for p in get_all_projects():
        if p.get("media_filename") == req.filename:
            matched_id = p["id"]
            break
            
    if matched_id:
        session_state["active_project_id"] = matched_id
    else:
        new_p_id = str(uuid.uuid4())
        media_id = str(uuid.uuid4())
        now_iso = utc_now_iso()
        meta["filename"] = req.filename
        p_state = create_default_project_state(meta)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (new_p_id, v_base, f"Project for {req.filename}", json.dumps(p_state), now_iso, now_iso))
            cursor.execute("""
            INSERT INTO media_assets (
                id, project_id, original_path, filename, duration, width, height, fps, codec, audio_available, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                media_id, new_p_id, target, req.filename, meta["duration"], meta["width"], meta["height"], meta["fps"], "h264", 1, now_iso
            ))
        session_state["active_project_id"] = new_p_id

    return get_session()

@app.post("/api/import/youtube")
def import_youtube(req: YouTubeImportRequest):
    """Validates URL and downloads remote video using yt-dlp."""
    validated_url = validate_remote_url(req.url)

    try:
        downloaded = download_youtube_video(validated_url, UPLOAD_DIR)
        meta = get_video_info(downloaded)
        session_state["video_path"] = downloaded
        session_state["video_meta"] = meta
        v_base = os.path.splitext(os.path.basename(downloaded))[0]
        p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
        extract_preview_frame(downloaded, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
        session_state["preview_frame"] = p_frame
        session_state["timeline_thumbs"] = extract_timeline_thumbnails(downloaded, CACHE_DIR, meta["duration"], count=6)
        session_state["discovered_clips"] = []

        # Create persistent SQLite project
        new_p_id = str(uuid.uuid4())
        media_id = str(uuid.uuid4())
        now_iso = utc_now_iso()
        f_name = os.path.basename(downloaded)
        meta["filename"] = f_name
        p_state = create_default_project_state(meta)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (new_p_id, v_base, f"Imported stream: {f_name}", json.dumps(p_state), now_iso, now_iso))
            cursor.execute("""
            INSERT INTO media_assets (
                id, project_id, original_path, filename, duration, width, height, fps, codec, audio_available, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                media_id, new_p_id, downloaded, f_name, meta["duration"], meta["width"], meta["height"], meta["fps"], "h264", 1, now_iso
            ))
        session_state["active_project_id"] = new_p_id

        return get_session()
    except Exception as e:
        logger.error(f"YouTube import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/import/upload")
async def import_upload(file: UploadFile = File(...)):
    """Safely streams uploaded video file to disk with filename sanitization and chunked writes."""
    safe_name = sanitize_filename(file.filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed video formats: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
        )

    target_path = get_safe_storage_path(safe_name, UPLOAD_DIR)

    # Stream write in 1MB chunks to prevent memory spikes on multi-GB recordings
    total_written = 0
    with open(target_path, "wb") as f_out:
        while chunk := await file.read(1024 * 1024):
            total_written += len(chunk)
            if total_written > MAX_FILE_SIZE_BYTES:
                f_out.close()
                os.remove(target_path)
                raise HTTPException(status_code=413, detail="File exceeds maximum allowed limit (10 GB)")
            f_out.write(chunk)

    try:
        meta = get_video_info(target_path)
    except Exception as e:
        if os.path.exists(target_path):
            os.remove(target_path)
        logger.warning(f"Uploaded file failed video validation: {e}")
        raise HTTPException(status_code=400, detail="Corrupt or invalid video file: could not read video stream")

    session_state["video_path"] = target_path
    session_state["video_meta"] = meta
    v_base = os.path.splitext(safe_name)[0]
    p_frame = os.path.join(CACHE_DIR, f"{v_base}_preview.jpg")
    extract_preview_frame(target_path, p_frame, timestamp=min(45.0, meta["duration"] * 0.2))
    session_state["preview_frame"] = p_frame
    session_state["timeline_thumbs"] = extract_timeline_thumbnails(target_path, CACHE_DIR, meta["duration"], count=6)
    session_state["discovered_clips"] = []

    # Create persistent SQLite project for uploaded video
    new_p_id = str(uuid.uuid4())
    media_id = str(uuid.uuid4())
    now_iso = utc_now_iso()
    meta["filename"] = safe_name
    p_state = create_default_project_state(meta)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (new_p_id, v_base, f"Uploaded: {safe_name}", json.dumps(p_state), now_iso, now_iso))
        cursor.execute("""
        INSERT INTO media_assets (
            id, project_id, original_path, filename, duration, width, height, fps, codec, audio_available, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            media_id, new_p_id, target_path, safe_name, meta["duration"], meta["width"], meta["height"], meta["fps"], "h264", 1, now_iso
        ))
    session_state["active_project_id"] = new_p_id

    return get_session()

@app.get("/api/frame")
def get_frame_at_timestamp(timestamp: float = 0.0):
    """Extracts a preview snapshot frame at a specified timestamp."""
    v_path = session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video in session")

    ts = max(0.0, timestamp)
    v_base = os.path.splitext(os.path.basename(v_path))[0]
    out_jpg = os.path.join(CACHE_DIR, f"{v_base}_frame_{int(ts)}s.jpg")
    extract_preview_frame(v_path, out_jpg, timestamp=ts)

    rel_p = os.path.relpath(out_jpg, STORAGE_DIR).replace("\\", "/")
    return {"timestamp": ts, "url": f"/storage/{rel_p}"}

@app.get("/api/media/waveform")
def get_media_waveform(
    filename: Optional[str] = None,
    video_path: Optional[str] = None,
    num_samples: int = 300
):
    """
    Returns normalized audio peaks waveform for the active session or requested video.
    Cached in storage/cache/<filename>_waveform_<num_samples>.json for instant load.
    """
    v_path = None
    if video_path:
        v_path = os.path.abspath(video_path)
    elif filename:
        v_path = get_safe_storage_path(filename, UPLOAD_DIR)
    else:
        v_path = session_state.get("video_path")
        
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=404, detail="Requested video file does not exist")
        
    try:
        data = generate_audio_waveform(v_path, CACHE_DIR, num_samples=num_samples)
        return data
    except Exception as e:
        logger.error(f"Waveform generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video/trim")
def trim_current_video(req: TrimVideoRequest):
    """
    Trims current video between start_time and end_time.
    Supports Mode A: Fast Keyframe Trim and Mode B: Accurate Frame Trim.
    """
    v_path = req.video_path or session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video to trim")

    duration = session_state.get("video_meta", {}).get("duration", 0.0)
    if req.start_time >= req.end_time:
        raise HTTPException(status_code=400, detail="start_time must be strictly less than end_time")
    if duration > 0 and req.start_time >= duration:
        raise HTTPException(status_code=400, detail="start_time exceeds total video duration")

    v_base = os.path.splitext(os.path.basename(v_path))[0]
    trimmed_name = f"{v_base}_trim_{int(req.start_time)}s.mp4"
    trimmed_path = get_safe_storage_path(trimmed_name, UPLOAD_DIR)

    trim_res = trim_video(v_path, trimmed_path, req.start_time, req.end_time, mode=req.mode)

    if not os.path.exists(trimmed_path):
        raise HTTPException(status_code=500, detail="Trim operation failed to create output file")

    meta = get_video_info(trimmed_path)
    session_state["video_path"] = trimmed_path
    session_state["video_meta"] = meta
    p_frame = os.path.join(CACHE_DIR, f"{os.path.splitext(trimmed_name)[0]}_preview.jpg")
    extract_preview_frame(trimmed_path, p_frame, timestamp=min(5.0, meta["duration"] * 0.2))
    session_state["preview_frame"] = p_frame
    session_state["timeline_thumbs"] = extract_timeline_thumbnails(trimmed_path, CACHE_DIR, meta["duration"], count=8)
    session_state["discovered_clips"] = []

    # Update or create project in SQLite
    new_p_id = str(uuid.uuid4())
    media_id = str(uuid.uuid4())
    now_iso = utc_now_iso()
    meta["filename"] = trimmed_name
    p_state = create_default_project_state(meta)
    p_state["timeline"]["pre_roll_cut"] = req.start_time
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (new_p_id, f"{v_base} (Trimmed)", f"Trimmed at {req.start_time}s ({trim_res['mode']})", json.dumps(p_state), now_iso, now_iso))
        cursor.execute("""
        INSERT INTO media_assets (
            id, project_id, original_path, filename, duration, width, height, fps, codec, audio_available, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            media_id, new_p_id, trimmed_path, trimmed_name, meta["duration"], meta["width"], meta["height"], meta["fps"], "h264", 1, now_iso
        ))
    session_state["active_project_id"] = new_p_id

    sess = get_session()
    sess["success"] = True
    sess["trimmed_video_path"] = trimmed_path
    sess["mode"] = trim_res.get("mode", req.mode)
    sess["project_id"] = new_p_id
    sess["trim_result"] = trim_res
    return sess

@app.post("/api/highlights/scan")
def scan_highlights(req: ScanHighlightsRequest):
    """Scans audio with Faster-Whisper on GPU and discovers highlights using Ollama."""
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

        # Persist discovered clips into clip_moments table
        proj_id = session_state.get("active_project_id")
        if proj_id:
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM media_assets WHERE project_id = ? LIMIT 1", (proj_id,))
                    m_row = cursor.fetchone()
                    media_id = m_row["id"] if m_row else None
                    for c in clips:
                        c_id = str(uuid.uuid4())
                        cursor.execute("""
                        INSERT INTO clip_moments (
                            id, project_id, media_asset_id, start_time, end_time, category, hook_text, highlight_score, selected, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            c_id,
                            proj_id,
                            media_id,
                            float(c.get("start", 0.0)),
                            float(c.get("end", 30.0)),
                            str(c.get("label", "Highlight")),
                            str(c.get("reason", ""))[:120],
                            float(c.get("score", 8.0)),
                            1,
                            utc_now_iso()
                        ))
            except Exception as ex:
                logger.warning(f"Could not persist clip moments to SQLite: {ex}")

        return {"clips": clips}
    except Exception as e:
        logger.error(f"Highlight scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_render_task(req: RenderRequest, job_id: Optional[str] = None, proj_id: Optional[str] = None):
    """Background rendering worker using NVIDIA NVENC with SQLite persistence."""
    v_path = session_state.get("video_path")
    if not v_path:
        session_state["render_job"] = {"status": "error", "progress": 0, "message": "No video loaded"}
        if job_id:
            try:
                with get_db() as conn:
                    conn.execute("UPDATE render_jobs SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?", ("No video loaded", utc_now_iso(), job_id))
            except Exception:
                pass
        return

    try:
        session_state["render_job"] = {"status": "running", "progress": 5, "message": "Starting GPU render...", "results": []}

        def on_prog(title, pct, msg):
            session_state["render_job"]["progress"] = int(pct)
            session_state["render_job"]["message"] = f"{title}: {msg}"
            if job_id:
                try:
                    with get_db() as conn:
                        conn.execute("UPDATE render_jobs SET progress = ?, updated_at = ? WHERE id = ?", (int(pct), utc_now_iso(), job_id))
                except Exception:
                    pass

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

        for r in results:
            rel_vp = os.path.relpath(r["video_path"], STORAGE_DIR).replace("\\", "/")
            r["video_url"] = f"/storage/{rel_vp}"

        session_state["render_job"] = {
            "status": "complete",
            "progress": 100,
            "message": "Render completed successfully!",
            "results": results
        }

        if job_id:
            primary_out = results[0]["video_path"] if results else ""
            try:
                with get_db() as conn:
                    conn.execute("""
                    UPDATE render_jobs
                    SET status = 'completed', progress = 100, output_path = ?, updated_at = ?
                    WHERE id = ?
                    """, (primary_out, utc_now_iso(), job_id))
            except Exception as ex:
                logger.warning(f"Could not update completed render job: {ex}")

    except Exception as e:
        logger.error(f"Render failed: {e}")
        session_state["render_job"] = {
            "status": "error",
            "progress": 0,
            "message": f"Render failed: {str(e)}",
            "results": []
        }
        if job_id:
            try:
                with get_db() as conn:
                    conn.execute("""
                    UPDATE render_jobs
                    SET status = 'failed', error_message = ?, updated_at = ?
                    WHERE id = ?
                    """, (str(e), utc_now_iso(), job_id))
            except Exception:
                pass

@app.post("/api/render")
def trigger_render(req: RenderRequest, bg_tasks: BackgroundTasks):
    """Triggers background GPU render job and records it in SQLite."""
    v_path = session_state.get("video_path")
    if not v_path or not os.path.exists(v_path):
        raise HTTPException(status_code=400, detail="No active video in session")
    if not req.clips:
        raise HTTPException(status_code=400, detail="No clips specified to render")

    # Ensure we have a valid project_id
    proj_id = session_state.get("active_project_id")
    if not proj_id:
        v_name = os.path.basename(v_path)
        for p in get_all_projects():
            if p.get("media_filename") == v_name:
                proj_id = p["id"]
                session_state["active_project_id"] = proj_id
                break
        if not proj_id:
            proj_id = str(uuid.uuid4())
            with get_db() as conn:
                conn.execute("""
                INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    proj_id,
                    os.path.splitext(v_name)[0],
                    "Render project",
                    json.dumps(create_default_project_state(session_state.get("video_meta"))),
                    utc_now_iso(),
                    utc_now_iso()
                ))
            session_state["active_project_id"] = proj_id

    job_id = str(uuid.uuid4())
    now_iso = utc_now_iso()
    try:
        with get_db() as conn:
            conn.execute("""
            INSERT INTO render_jobs (id, project_id, status, progress, render_settings_json, created_at, updated_at)
            VALUES (?, ?, 'rendering', 0, ?, ?, ?)
            """, (
                job_id,
                proj_id,
                json.dumps({
                    "layout_mode": req.layout_mode,
                    "clips_count": len(req.clips),
                    "subtitle_theme": req.subtitle_theme
                }),
                now_iso,
                now_iso
            ))
    except Exception as ex:
        logger.warning(f"Could not record render job in SQLite: {ex}")

    bg_tasks.add_task(run_render_task, req, job_id, proj_id)
    return {"status": "started", "job_id": job_id, "message": f"Rendering {len(req.clips)} clips in background..."}

@app.get("/api/render/status")
def get_render_status():
    """Returns status and progress percentage of background render job."""
    return session_state.get("render_job", {"status": "idle"})

@app.get("/api/library")
def get_library():
    """Lists finished rendered shorts from storage/outputs."""
    shorts = [
        f for f in os.listdir(OUTPUTS_DIR)
        if os.path.splitext(f)[1].lower() in ALLOWED_VIDEO_EXTENSIONS and not f.startswith(".")
    ]
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
    # Strictly bind to localhost 127.0.0.1 for local-first desktop security
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
