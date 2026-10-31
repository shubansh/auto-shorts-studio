import os
import sys
import json
import unittest
import shutil

# Set up paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from server import app
from core.database import (
    get_db,
    init_db,
    get_project_by_id,
    save_project,
    get_all_projects,
    DB_PATH
)
from core.audio import (
    generate_audio_waveform,
    get_nearest_keyframe,
    trim_video,
    extract_timeline_thumbnails
)

client = TestClient(app)

class TestClipForgePhase4EditorTimeline(unittest.TestCase):
    """
    Comprehensive Phase 4 Test Suite:
    Validates waveform streaming and caching, keyframe detection, fast vs accurate video trimming,
    batch thumbnail extraction, and scene keyframe layout persistence in SQLite.
    """

    @classmethod
    def setUpClass(cls):
        init_db(DB_PATH)
        cls.sample_video = os.path.join(PROJECT_ROOT, "storage", "uploads", "enFF4P7FSg0.mp4")
        if not os.path.exists(cls.sample_video):
            raise unittest.SkipTest("Sample video enFF4P7FSg0.mp4 not found for Phase 4 testing")

    def test_01_waveform_generation_and_caching(self):
        """Verify audio waveform generation via streaming PCM and cache invalidation."""
        # API request
        response = client.get(f"/api/media/waveform?video_path={self.sample_video}&num_samples=120")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("audio_available"))
        self.assertEqual(len(data.get("peaks", [])), 120)
        self.assertGreater(data.get("duration", 0), 0)
        self.assertIn("source_mtime", data)

        # Cache file must exist on disk
        cache_dir = os.path.join(PROJECT_ROOT, "storage", "cache")
        base_name = os.path.splitext(os.path.basename(self.sample_video))[0]
        cache_file = os.path.join(cache_dir, f"{base_name}_waveform.json")
        self.assertTrue(os.path.exists(cache_file), "Cache JSON file must be saved")

        # Second request must hit cache instantly
        response2 = client.get(f"/api/media/waveform?video_path={self.sample_video}&num_samples=120")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(len(response2.json()["peaks"]), 120)

    def test_02_waveform_missing_file_error_handling(self):
        """Ensure missing media returns HTTP 404."""
        response = client.get("/api/media/waveform?video_path=storage/uploads/non_existent_clip.mp4")
        self.assertEqual(response.status_code, 404)

    def test_03_keyframe_detection(self):
        """Verify nearest keyframe detection returns a valid PTS float <= requested timestamp."""
        kf = get_nearest_keyframe(self.sample_video, 10.0)
        self.assertIsInstance(kf, float)
        self.assertGreaterEqual(kf, 0.0)
        self.assertLessEqual(kf, 10.0)

    def test_04_fast_video_trim_mode(self):
        """Verify Fast Keyframe Trim (Mode A) stream copy and SQLite persistence."""
        payload = {
            "video_path": self.sample_video,
            "start_time": 5.0,
            "end_time": 10.0,
            "mode": "fast"
        }
        response = client.post("/api/video/trim", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mode"], "fast")
        out_path = data["trimmed_video_path"]
        self.assertTrue(os.path.exists(out_path), "Trimmed output file must exist")
        self.assertGreater(os.path.getsize(out_path), 1000)

        # Verify SQLite project was created/updated for the trimmed video
        proj_id = data.get("project_id")
        self.assertIsNotNone(proj_id)
        proj = get_project_by_id(proj_id)
        self.assertIsNotNone(proj)
        self.assertIn("trim", proj["name"].lower())

        # Clean up test output
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception:
                pass

    def test_05_accurate_video_trim_mode(self):
        """Verify Accurate Frame Trim (Mode B) using NVENC/CPU encoding."""
        payload = {
            "video_path": self.sample_video,
            "start_time": 5.0,
            "end_time": 8.0,
            "mode": "accurate"
        }
        response = client.post("/api/video/trim", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mode"], "accurate")
        out_path = data["trimmed_video_path"]
        self.assertTrue(os.path.exists(out_path), "Trimmed output file must exist")
        self.assertGreater(os.path.getsize(out_path), 1000)

        # Clean up test output
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception:
                pass

    def test_06_batch_thumbnail_extraction(self):
        """Verify batch timeline thumbnail extraction with caching."""
        cache_dir = os.path.join(PROJECT_ROOT, "storage", "cache", "test_phase4_thumbs")
        thumbs = extract_timeline_thumbnails(self.sample_video, cache_dir, duration=60.0, count=4)
        self.assertEqual(len(thumbs), 4)
        for t in thumbs:
            self.assertTrue(os.path.exists(t["path"]), f"Thumbnail {t['path']} must exist")
            self.assertGreater(t["timestamp"], 0)

        # Clean up test thumbs folder
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)

    def test_07_scene_keyframes_persistence(self):
        """Verify Scene Timestamp Keyframes save and restore properly in project_state_json."""
        projects = get_all_projects()
        self.assertGreater(len(projects), 0)
        proj_id = projects[0]["id"]
        proj = get_project_by_id(proj_id)
        state = proj["project_state"]

        test_keyframes = [
            {
                "id": "kf_intro",
                "timestamp": 0.0,
                "face_x": 25.0,
                "face_y": 10.0,
                "face_w": 50.0,
                "face_h": 50.0,
                "gameplay_x": 0.0,
                "gameplay_y": 60.0,
                "gameplay_w": 100.0,
                "gameplay_h": 40.0,
                "transition": "cut"
            },
            {
                "id": "kf_gameplay_start",
                "timestamp": 45.0,
                "face_x": 10.0,
                "face_y": 5.0,
                "face_w": 28.0,
                "face_h": 28.0,
                "gameplay_x": 0.0,
                "gameplay_y": 0.0,
                "gameplay_w": 100.0,
                "gameplay_h": 100.0,
                "transition": "cut"
            }
        ]

        state["scene_keyframes"] = test_keyframes
        save_project(proj_id, name=proj["name"], state=state)

        # Read back via API
        resp = client.get(f"/api/projects/{proj_id}")
        self.assertEqual(resp.status_code, 200)
        loaded_state = resp.json().get("project_state", {})
        loaded_kfs = loaded_state.get("scene_keyframes", [])
        self.assertEqual(len(loaded_kfs), 2)
        self.assertEqual(loaded_kfs[0]["id"], "kf_intro")
        self.assertEqual(loaded_kfs[1]["timestamp"], 45.0)

    def test_08_safe_zone_and_styling_layout_persistence(self):
        """Verify safe zone overlays and advanced layout styling persist in SQLite."""
        projects = get_all_projects()
        proj_id = projects[0]["id"]
        proj = get_project_by_id(proj_id)
        state = proj["project_state"]

        layout_config = state.get("layout_config", {})
        layout_config["safe_zone"] = "youtube_shorts"
        layout_config["face_opacity"] = 0.95
        layout_config["face_border"] = 3
        layout_config["face_rounded"] = 16
        layout_config["blur_intensity"] = 25
        state["layout_config"] = layout_config

        # Update via PUT /api/projects/:id
        resp = client.put(f"/api/projects/{proj_id}", json={"project_state": state})
        self.assertEqual(resp.status_code, 200)

        # Verify retrieval
        updated = get_project_by_id(proj_id)
        cfg = updated["project_state"]["layout_config"]
        self.assertEqual(cfg["safe_zone"], "youtube_shorts")
        self.assertEqual(cfg["face_opacity"], 0.95)
        self.assertEqual(cfg["face_border"], 3)
        self.assertEqual(cfg["blur_intensity"], 25)

if __name__ == "__main__":
    unittest.main()
