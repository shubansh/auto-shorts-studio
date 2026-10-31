import os
import sqlite3
import json
import logging
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any, List

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DB_PATH = os.path.join(STORAGE_DIR, "clipforge.db")

SCHEMA_VERSION = 1

def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Creates and configures a thread-safe SQLite connection.
    Enforces WAL mode, foreign keys, and sensible connection timeouts.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        timeout=25.0,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    # Configure production SQLite pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 25000;")
    return conn

@contextmanager
def get_db(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for safe database transactions.
    Automatically commits on completion or rolls back on exceptions.
    """
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise e
    finally:
        conn.close()

def init_db(db_path: str = DB_PATH) -> None:
    """
    Initializes all database tables, indexes, and initial settings.
    Handles schema migrations safely without data loss.
    """
    logger.info(f"Initializing ClipForge SQLite database at {db_path}...")
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Schema Version Tracking Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """)

        # 2. Projects Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            project_state_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # 3. Media Assets Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_assets (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            original_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            duration REAL DEFAULT 0.0,
            width INTEGER DEFAULT 1920,
            height INTEGER DEFAULT 1080,
            fps REAL DEFAULT 30.0,
            codec TEXT DEFAULT 'h264',
            audio_available INTEGER DEFAULT 1,
            proxy_path TEXT,
            thumbnail_path TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 4. Clip Moments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clip_moments (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            media_asset_id TEXT REFERENCES media_assets(id) ON DELETE SET NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            category TEXT DEFAULT 'Highlight',
            hook_text TEXT,
            highlight_score REAL DEFAULT 8.0,
            detection_metadata_json TEXT,
            selected INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)

        # 5. Render Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS render_jobs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            clip_moment_id TEXT REFERENCES clip_moments(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            progress INTEGER DEFAULT 0,
            output_path TEXT,
            error_message TEXT,
            render_settings_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # 6. System Settings Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # Indexes for high performance querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_project_id ON media_assets(project_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clip_moments_project_id ON clip_moments(project_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_render_jobs_project_id ON render_jobs(project_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_render_jobs_status ON render_jobs(status);")

        # Mark schema version if not present
        cursor.execute("SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?);",
                (SCHEMA_VERSION, utc_now_iso())
            )

        # Populate default system settings if missing
        default_settings = {
            "whisper_model": "small",
            "ollama_model": "llama3.2:latest",
            "preferred_resolution": "1080x1920",
            "preferred_fps": 60,
            "caption_theme": "Hormozi Gold (Viral)",
            "enable_emojis": True,
            "layout_preset": "gaming_split",
            "hardware_preferences": {
                "use_nvenc": True,
                "fallback_cpu": True,
                "compute_type": "float16"
            }
        }
        for k, v in default_settings.items():
            cursor.execute(
                "INSERT OR IGNORE INTO system_settings (key, value_json, updated_at) VALUES (?, ?, ?);",
                (k, json.dumps(v), utc_now_iso())
            )

        # Recover any interrupted render jobs from previous unclean shutdowns
        cursor.execute("""
        UPDATE render_jobs
        SET status = 'failed',
            error_message = 'Render job interrupted by application restart',
            updated_at = ?
        WHERE status IN ('rendering', 'queued');
        """, (utc_now_iso(),))

    logger.info("Database schema initialized and verified successfully.")


def create_default_project_state(media_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generates a non-destructive versioned default project state."""
    w = media_info.get("width", 1920) if media_info else 1920
    h = media_info.get("height", 1080) if media_info else 1080
    dur = media_info.get("duration", 60.0) if media_info else 60.0
    fps = media_info.get("fps", 30.0) if media_info else 30.0
    filename = media_info.get("filename", "") if media_info else ""

    return {
        "version": "1.0",
        "source_media": {
            "filename": filename,
            "duration": dur,
            "width": w,
            "height": h,
            "fps": fps
        },
        "timeline": {
            "in_point": 0.0,
            "out_point": min(30.0, dur),
            "pre_roll_cut": 0.0,
            "zoom": 1.0
        },
        "layout": {
            "mode": "gaming_split",
            "gaming_config": {
                "face_x": 65,
                "face_y": 58,
                "face_w": 33,
                "face_h": 40,
                "game_x": 5,
                "game_y": 5,
                "game_w": 90,
                "game_h": 90,
                "face_height_pct": 40
            },
            "single_crop_config": {
                "crop_x": 28,
                "crop_y": 0,
                "crop_w": 44,
                "crop_h": 100
            }
        },
        "captions": {
            "theme": "Hormozi Gold (Viral)",
            "enable_emojis": True,
            "corrections": {}
        },
        "render_settings": {
            "resolution": "1080x1920",
            "fps": 60,
            "encoder": "h264_nvenc"
        },
        "scene_keyframes": []
    }


def migrate_existing_uploads_to_projects(db_path: str = DB_PATH) -> int:
    """
    Seamless backward-compatibility migration:
    Scans storage/uploads for existing video files and ensures a project
    record exists for each, without modifying or re-encoding source media.
    """
    uploads_dir = os.path.join(STORAGE_DIR, "uploads")
    cache_dir = os.path.join(STORAGE_DIR, "cache")
    if not os.path.exists(uploads_dir):
        return 0

    allowed_exts = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    files = [
        f for f in os.listdir(uploads_dir)
        if os.path.splitext(f)[1].lower() in allowed_exts and not f.endswith(".part")
    ]
    if not files:
        return 0

    from core.audio import get_video_info

    migrated_count = 0
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        for f in files:
            full_path = os.path.join(uploads_dir, f)
            # Check if this file already has a media_asset record
            cursor.execute("SELECT id, project_id FROM media_assets WHERE filename = ?", (f,))
            existing = cursor.fetchone()
            if existing:
                continue

            # Need to create project + media_asset
            project_id = str(uuid.uuid4())
            media_id = str(uuid.uuid4())
            now_iso = utc_now_iso()

            try:
                meta = get_video_info(full_path)
            except Exception:
                meta = {"width": 1920, "height": 1080, "duration": 60.0, "fps": 30.0}

            meta["filename"] = f
            proj_state = create_default_project_state(meta)
            proj_name = os.path.splitext(f)[0]

            # 1. Insert Project
            cursor.execute("""
            INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                proj_name,
                f"Auto-imported project for {f}",
                json.dumps(proj_state),
                now_iso,
                now_iso
            ))

            # 2. Insert Media Asset
            cursor.execute("""
            INSERT INTO media_assets (
                id, project_id, original_path, filename, duration, width, height, fps, codec, audio_available, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                media_id,
                project_id,
                full_path,
                f,
                meta["duration"],
                meta["width"],
                meta["height"],
                meta["fps"],
                "h264",
                1,
                now_iso
            ))

            # 3. Check if cached transcript exists to populate clip moments
            t_cache = os.path.join(cache_dir, f"{os.path.splitext(f)[0]}_transcript.json")
            if os.path.exists(t_cache):
                try:
                    with open(t_cache, "r", encoding="utf-8") as tf:
                        t_data = json.load(tf)
                    # Create default highlight clip moments from transcript segments if present
                    segments = t_data.get("segments", [])
                    if segments:
                        clip_id = str(uuid.uuid4())
                        end_t = min(30.0, segments[-1]["end"])
                        cursor.execute("""
                        INSERT INTO clip_moments (
                            id, project_id, media_asset_id, start_time, end_time, category, hook_text, highlight_score, selected, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            clip_id,
                            project_id,
                            media_id,
                            0.0,
                            end_t,
                            "Highlight",
                            segments[0].get("text", "")[:100],
                            8.8,
                            1,
                            now_iso
                        ))
                except Exception as ex:
                    logger.warning(f"Could not migrate transcript clips for {f}: {ex}")

            migrated_count += 1
            logger.info(f"Migrated existing media '{f}' into project '{proj_name}' (ID: {project_id})")

    return migrated_count


# Database Repository Query Helpers
def get_all_projects(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.*, 
               m.filename as media_filename,
               m.duration as media_duration,
               m.width as media_width,
               m.height as media_height,
               (SELECT COUNT(*) FROM clip_moments c WHERE c.project_id = p.id) as clips_count,
               (SELECT COUNT(*) FROM render_jobs r WHERE r.project_id = p.id AND r.status = 'completed') as rendered_count
        FROM projects p
        LEFT JOIN media_assets m ON m.project_id = p.id
        ORDER BY p.updated_at DESC;
        """)
        rows = cursor.fetchall()
        projects = []
        for r in rows:
            d = dict(r)
            try:
                d["project_state"] = json.loads(d["project_state_json"])
            except Exception:
                d["project_state"] = {}
            projects.append(d)
        return projects


def get_project_by_id(project_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        p_row = cursor.fetchone()
        if not p_row:
            return None

        project = dict(p_row)
        try:
            project["project_state"] = json.loads(project["project_state_json"])
        except Exception:
            project["project_state"] = {}

        # Fetch associated media asset
        cursor.execute("SELECT * FROM media_assets WHERE project_id = ? LIMIT 1", (project_id,))
        m_row = cursor.fetchone()
        project["media_asset"] = dict(m_row) if m_row else None

        # Fetch clip moments
        cursor.execute("SELECT * FROM clip_moments WHERE project_id = ? ORDER BY start_time ASC", (project_id,))
        project["clips"] = [dict(c) for c in cursor.fetchall()]

        # Fetch recent render jobs
        cursor.execute("SELECT * FROM render_jobs WHERE project_id = ? ORDER BY created_at DESC LIMIT 10", (project_id,))
        project["render_jobs"] = [dict(j) for j in cursor.fetchall()]

        return project


def save_project(project_id: str, name: str, state: Dict[str, Any], description: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    now_iso = utc_now_iso()
    state_json = json.dumps(state)

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        exists = cursor.fetchone()

        if exists:
            cursor.execute("""
            UPDATE projects
            SET name = ?, description = COALESCE(?, description), project_state_json = ?, updated_at = ?
            WHERE id = ?
            """, (name, description, state_json, now_iso, project_id))
        else:
            cursor.execute("""
            INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, name, description or "", state_json, now_iso, now_iso))

    return get_project_by_id(project_id, db_path)


def delete_project_metadata(project_id: str, delete_media_files: bool = False, db_path: str = DB_PATH) -> bool:
    """
    Deletes project metadata.
    NEVER deletes original source media unless explicitly requested (delete_media_files=True).
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if delete_media_files:
            cursor.execute("SELECT original_path FROM media_assets WHERE project_id = ?", (project_id,))
            assets = cursor.fetchall()
            for a in assets:
                orig = a["original_path"]
                if orig and os.path.exists(orig):
                    try:
                        os.remove(orig)
                        logger.info(f"User requested file deletion for: {orig}")
                    except Exception as e:
                        logger.warning(f"Could not remove source file {orig}: {e}")

        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cursor.rowcount > 0


def get_all_settings(db_path: str = DB_PATH) -> Dict[str, Any]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value_json FROM system_settings")
        settings = {}
        for row in cursor.fetchall():
            try:
                settings[row["key"]] = json.loads(row["value_json"])
            except Exception:
                settings[row["key"]] = row["value_json"]
        return settings


def set_setting(key: str, value: Any, db_path: str = DB_PATH) -> None:
    now_iso = utc_now_iso()
    val_json = json.dumps(value)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO system_settings (key, value_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at;
        """, (key, val_json, now_iso))
