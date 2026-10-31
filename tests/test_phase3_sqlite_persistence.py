import os
import sys
import json
import sqlite3
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor

# Set up paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from server import app
from core.database import (
    get_db,
    get_db_connection,
    init_db,
    migrate_existing_uploads_to_projects,
    get_all_projects,
    get_project_by_id,
    save_project,
    delete_project_metadata,
    get_all_settings,
    set_setting,
    create_default_project_state,
    DB_PATH
)

client = TestClient(app)

class TestClipForgePhase3SQLitePersistence(unittest.TestCase):
    """
    Comprehensive Phase 3 Test Suite:
    Validates SQLite persistence, non-destructive versioned project state,
    render job recovery, system settings, and concurrent access.
    """

    def setUp(self):
        # Ensure database is initialized
        init_db(DB_PATH)

    def test_01_database_foundation_and_pragmas(self):
        """Verify SQLite WAL mode, foreign keys, and schema tables."""
        with get_db(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Check WAL journal mode
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0].lower()
            self.assertEqual(journal_mode, "wal", f"Expected WAL mode, got {journal_mode}")
            
            # Check Foreign Keys
            cursor.execute("PRAGMA foreign_keys;")
            fk = cursor.fetchone()[0]
            self.assertEqual(fk, 1, "Foreign keys must be enabled")
            
            # Check required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            expected_tables = {
                "schema_version",
                "projects",
                "media_assets",
                "clip_moments",
                "render_jobs",
                "system_settings"
            }
            for tbl in expected_tables:
                self.assertIn(tbl, tables, f"Missing expected table: {tbl}")

    def test_02_create_project_api(self):
        """Test POST /api/projects creates non-destructive project with version 1.0 state."""
        payload = {
            "name": "Phase 3 Test Project Alpha",
            "description": "Validation of SQLite persistence",
            "media_filename": None
        }
        res = client.post("/api/projects", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Phase 3 Test Project Alpha")
        self.assertIn("project_state", data)
        
        state = data["project_state"]
        self.assertEqual(state.get("version"), "1.0")
        self.assertIn("timeline", state)
        self.assertIn("layout", state)
        self.assertIn("captions", state)
        self.assertIn("render_settings", state)
        
        # Cleanup
        client.delete(f"/api/projects/{data['id']}")

    def test_03_project_listing_and_retrieval(self):
        """Test GET /api/projects and GET /api/projects/{id}."""
        # Create a test project
        res_create = client.post("/api/projects", json={
            "name": "Project Listing Test",
            "description": "To test list and get by id"
        })
        self.assertEqual(res_create.status_code, 200)
        proj_id = res_create.json()["id"]

        # List projects
        res_list = client.get("/api/projects")
        self.assertEqual(res_list.status_code, 200)
        projects = res_list.json()
        self.assertIsInstance(projects, list)
        matched = [p for p in projects if p["id"] == proj_id]
        self.assertEqual(len(matched), 1)

        # Get project by ID
        res_get = client.get(f"/api/projects/{proj_id}")
        self.assertEqual(res_get.status_code, 200)
        proj_detail = res_get.json()
        self.assertEqual(proj_detail["id"], proj_id)
        self.assertEqual(proj_detail["name"], "Project Listing Test")

        # Cleanup
        client.delete(f"/api/projects/{proj_id}")

    def test_04_non_destructive_project_update(self):
        """Test PUT /api/projects/{id} updates state without breaking schema."""
        # Create project
        res_create = client.post("/api/projects", json={"name": "Before Update Project"})
        proj_id = res_create.json()["id"]
        orig_state = res_create.json()["project_state"]

        # Modify layout and captions
        orig_state["layout"]["mode"] = "crop"
        orig_state["layout"]["single_crop_config"]["crop_x"] = 35
        orig_state["captions"]["theme"] = "MrBeast Modern"

        res_update = client.put(f"/api/projects/{proj_id}", json={
            "name": "Updated Project Name",
            "description": "Updated non-destructively",
            "project_state": orig_state
        })
        self.assertEqual(res_update.status_code, 200)
        updated = res_update.json()

        self.assertEqual(updated["name"], "Updated Project Name")
        self.assertEqual(updated["project_state"]["layout"]["mode"], "crop")
        self.assertEqual(updated["project_state"]["layout"]["single_crop_config"]["crop_x"], 35)
        self.assertEqual(updated["project_state"]["captions"]["theme"], "MrBeast Modern")

        # Cleanup
        client.delete(f"/api/projects/{proj_id}")

    def test_05_update_rejects_empty_name(self):
        """Verify PUT /api/projects/{id} rejects empty name."""
        res_create = client.post("/api/projects", json={"name": "Valid Name"})
        proj_id = res_create.json()["id"]

        res_bad = client.put(f"/api/projects/{proj_id}", json={"name": "   "})
        self.assertEqual(res_bad.status_code, 400)

        # Cleanup
        client.delete(f"/api/projects/{proj_id}")

    def test_06_delete_project_preserves_source_media(self):
        """Test DELETE /api/projects/{id} removes metadata but keeps source file intact."""
        # Create a dummy media file in storage/uploads
        dummy_file = os.path.join(PROJECT_ROOT, "storage", "uploads", "dummy_safety_test.mp4")
        with open(dummy_file, "wb") as f:
            f.write(b"0" * 1024)

        try:
            res_create = client.post("/api/projects", json={
                "name": "Safety Media Test Project",
                "media_filename": "dummy_safety_test.mp4"
            })
            self.assertEqual(res_create.status_code, 200)
            proj_id = res_create.json()["id"]

            # Delete project with delete_media=False (default)
            res_del = client.delete(f"/api/projects/{proj_id}")
            self.assertEqual(res_del.status_code, 200)
            self.assertEqual(res_del.json()["media_deleted"], False)

            # Confirm project is deleted from DB
            res_check = client.get(f"/api/projects/{proj_id}")
            self.assertEqual(res_check.status_code, 404)

            # Confirm source file STILL EXISTS on disk!
            self.assertTrue(os.path.exists(dummy_file), "Source media MUST NOT be deleted!")

        finally:
            if os.path.exists(dummy_file):
                os.remove(dummy_file)

    def test_07_system_settings_api(self):
        """Test GET and POST /api/settings persistence."""
        res_get = client.get("/api/settings")
        self.assertEqual(res_get.status_code, 200)
        settings = res_get.json()
        self.assertIn("whisper_model", settings)
        self.assertIn("preferred_fps", settings)

        # Update a setting
        res_post = client.post("/api/settings", json={
            "settings": {
                "whisper_model": "base",
                "preferred_fps": 60,
                "custom_test_key": "persisted_value"
            }
        })
        self.assertEqual(res_post.status_code, 200)
        updated_settings = res_post.json()
        self.assertEqual(updated_settings["whisper_model"], "base")
        self.assertEqual(updated_settings["preferred_fps"], 60)
        self.assertEqual(updated_settings["custom_test_key"], "persisted_value")

    def test_08_interrupted_render_job_recovery(self):
        """Test that uncompleted render jobs are marked failed on startup/init_db."""
        # Insert a simulated interrupted render job
        with get_db(DB_PATH) as conn:
            # Create a test project for it
            conn.execute("""
            INSERT OR REPLACE INTO projects (id, name, description, project_state_json, created_at, updated_at)
            VALUES ('test_crash_proj', 'Crash Recovery Proj', '', '{}', '2026-01-01', '2026-01-01');
            """)
            conn.execute("""
            INSERT OR REPLACE INTO render_jobs (id, project_id, status, progress, created_at, updated_at)
            VALUES ('test_crash_job', 'test_crash_proj', 'rendering', 42, '2026-01-01', '2026-01-01');
            """)

        # Call init_db (simulating restart)
        init_db(DB_PATH)

        # Verify job was recovered
        with get_db(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, error_message FROM render_jobs WHERE id = 'test_crash_job'")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "failed")
            self.assertIn("restart", row[1].lower())

            # Cleanup
            conn.execute("DELETE FROM render_jobs WHERE id = 'test_crash_job'")
            conn.execute("DELETE FROM projects WHERE id = 'test_crash_proj'")

    def test_09_sqlite_concurrency(self):
        """Test multiple concurrent reader and writer threads without SQLite lock errors."""
        res = client.post("/api/projects", json={"name": "Concurrency Master Project"})
        proj_id = res.json()["id"]

        errors = []

        def worker_task(thread_idx: int):
            try:
                # Alternate reading and updating
                if thread_idx % 2 == 0:
                    r = client.get(f"/api/projects/{proj_id}")
                    if r.status_code != 200:
                        errors.append(f"Thread {thread_idx} GET failed: {r.status_code}")
                else:
                    r = client.put(f"/api/projects/{proj_id}", json={
                        "name": f"Concurrency Project Iteration {thread_idx}"
                    })
                    if r.status_code != 200:
                        errors.append(f"Thread {thread_idx} PUT failed: {r.status_code}")
            except Exception as e:
                errors.append(f"Thread {thread_idx} exception: {e}")

        threads = []
        for i in range(15):
            t = threading.Thread(target=worker_task, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors occurred: {errors}")

        # Cleanup
        client.delete(f"/api/projects/{proj_id}")

if __name__ == "__main__":
    unittest.main()
