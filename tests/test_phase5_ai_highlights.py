import os
import sys
import json
import unittest
import uuid
from unittest.mock import patch

# Set up paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from server import app
from core.database import get_db, init_db, DB_PATH
from core.audio_intelligence import analyze_audio_signals
from core.visual_intelligence import analyze_visual_signals, GAME_PRESETS
from core.highlight_fusion import (
    fuse_multimodal_candidates,
    calculate_hqs,
    merge_overlapping_windows
)
from core.highlight_detector import (
    HighlightDetector,
    clean_json_response,
    get_available_ollama_models
)
from core.transcriber import AudioTranscriber

client = TestClient(app)

class TestClipForgePhase5AIHighlights(unittest.TestCase):
    """
    Comprehensive Phase 5 Test Suite:
    Validates Multi-Signal AI Highlight Intelligence Engine:
    - Audio Intelligence (RMS, Silence VAD, Screams, Gunshots, Transients)
    - Visual Intelligence (OpenCV Adaptive Sampling, Motion Flux, Scene Cuts)
    - Multimodal Candidate Fusion (Setup + Climax + Payoff, Sentence Snapping, NMS Deduplication)
    - Explainable HQS (Hook 25%, Audio 20%, Event 25%, Context 20%, Visual 10%)
    - Ollama Contextual LLM Integration & Deterministic Fallback
    - Faster-Whisper GPU VRAM Sequential Release
    - Background Scan Job Endpoints & SQLite Persistence
    """

    @classmethod
    def setUpClass(cls):
        init_db(DB_PATH)
        cls.sample_video = os.path.join(PROJECT_ROOT, "storage", "uploads", "enFF4P7FSg0.mp4")
        cls.cache_dir = os.path.join(PROJECT_ROOT, "storage", "cache")
        os.makedirs(cls.cache_dir, exist_ok=True)
        if not os.path.exists(cls.sample_video):
            raise unittest.SkipTest("Sample video enFF4P7FSg0.mp4 not found for Phase 5 testing")

    def test_01_audio_intelligence_signal_extraction(self):
        """Verify audio intelligence extracts RMS energy, silence intervals, and audio events."""
        audio_signals = analyze_audio_signals(self.sample_video, self.cache_dir, silence_thresh_db=-38.0)
        self.assertIn("audio_events", audio_signals)
        self.assertIn("silence_intervals", audio_signals)
        self.assertIn("mean_rms_db", audio_signals)
        self.assertIsInstance(audio_signals["audio_events"], list)
        self.assertIsInstance(audio_signals["silence_intervals"], list)

        # Cache file should exist
        base_name = os.path.splitext(os.path.basename(self.sample_video))[0]
        cache_path = os.path.join(self.cache_dir, f"{base_name}_audio_signals.json")
        self.assertTrue(os.path.exists(cache_path), "Audio intelligence cache must exist on disk")

        # Second run should load from cache
        cached_signals = analyze_audio_signals(self.sample_video, self.cache_dir)
        self.assertEqual(len(cached_signals["audio_events"]), len(audio_signals["audio_events"]))

    def test_02_visual_intelligence_motion_and_presets(self):
        """Verify OpenCV adaptive sampling, motion curve, scene cuts, and game presets."""
        self.assertIn("valorant", GAME_PRESETS)
        self.assertIn("cs2", GAME_PRESETS)
        self.assertIn("minecraft", GAME_PRESETS)

        visual_signals = analyze_visual_signals(
            self.sample_video,
            self.cache_dir,
            game_type="valorant",
            audio_events=[{"timestamp": 12.0, "type": "scream", "intensity": 0.85}]
        )
        self.assertIn("scene_transitions", visual_signals)
        self.assertIn("action_bursts", visual_signals)
        self.assertIn("game_type", visual_signals)
        self.assertEqual(visual_signals["game_type"], "valorant")

        # Cache file check
        base_name = os.path.splitext(os.path.basename(self.sample_video))[0]
        cache_path = os.path.join(self.cache_dir, f"{base_name}_visual_signals.json")
        self.assertTrue(os.path.exists(cache_path), "Visual intelligence cache must exist on disk")

    def test_03_multimodal_fusion_and_windowing(self):
        """Verify candidate anchor fusion, sentence snapping, and setup+climax+payoff windowing."""
        dummy_audio = {
            "audio_events": [
                {"timestamp": 25.0, "type": "scream", "intensity": 0.95, "duration": 1.2},
                {"timestamp": 45.0, "type": "laughter", "intensity": 0.85, "duration": 2.0}
            ],
            "silence_intervals": [[0.0, 5.0]]
        }
        dummy_visual = {
            "action_bursts": [
                {"timestamp": 24.5, "motion_score": 0.88, "type": "high_motion"}
            ],
            "scene_transitions": [20.0, 35.0]
        }
        dummy_transcript = {
            "segments": [
                {
                    "start": 20.0,
                    "end": 28.0,
                    "text": "Bhai headshot mara OP clutch tha!",
                    "words": [
                        {"word": "Bhai", "start": 20.0, "end": 20.5},
                        {"word": "headshot", "start": 20.6, "end": 22.0},
                        {"word": "mara", "start": 22.1, "end": 23.0},
                        {"word": "OP", "start": 24.0, "end": 25.0},
                        {"word": "clutch", "start": 25.1, "end": 26.5},
                        {"word": "tha", "start": 26.6, "end": 28.0}
                    ]
                }
            ]
        }

        candidates = fuse_multimodal_candidates(
            dummy_audio,
            dummy_visual,
            dummy_transcript,
            total_duration=60.0,
            min_duration=15,
            max_duration=35,
            scan_start=0.0
        )
        self.assertGreaterEqual(len(candidates), 1)
        top = candidates[0]
        self.assertIn("start", top)
        self.assertIn("end", top)
        self.assertIn("hqs", top)
        self.assertIn("hqs_breakdown", top)
        self.assertGreaterEqual(top["hqs"], 50.0)
        self.assertLessEqual(top["hqs"], 100.0)

    def test_04_explainable_hqs_calculation(self):
        """Verify HQS (0-100) and each sub-score respects weighted bounds."""
        hqs, breakdown = calculate_hqs(
            hook_strength=0.9,
            audio_intensity=0.8,
            event_type_weight=0.95,
            context_coherence=0.85,
            visual_motion=0.7
        )
        self.assertGreaterEqual(hqs, 0)
        self.assertLessEqual(hqs, 100)
        # Sub-score bounds: hook max 25, audio max 20, event max 25, context max 20, visual max 10
        self.assertLessEqual(breakdown["hook"], 25.0)
        self.assertLessEqual(breakdown["audio"], 20.0)
        self.assertLessEqual(breakdown["event"], 25.0)
        self.assertLessEqual(breakdown["context"], 20.0)
        self.assertLessEqual(breakdown["visual"], 10.0)
        total_sum = sum(breakdown.values())
        self.assertAlmostEqual(hqs, total_sum, delta=0.2)

    def test_05_nms_window_deduplication(self):
        """Verify Non-Maximum Suppression merges overlapping candidate moments (>45%)."""
        windows = [
            {"start": 10.0, "end": 35.0, "hqs": 80.0},
            {"start": 14.0, "end": 38.0, "hqs": 92.0},  # Heavy overlap -> higher score wins
            {"start": 50.0, "end": 75.0, "hqs": 75.0}   # Disjoint window
        ]
        merged = merge_overlapping_windows(windows, iou_threshold=0.45)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["hqs"], 92.0)

    def test_06_transcriber_vram_release(self):
        """Verify AudioTranscriber provides release_vram() for sequential GPU memory budgeting."""
        transcriber = AudioTranscriber(model_size="tiny")
        self.assertTrue(hasattr(transcriber, "release_vram"))
        # Must execute cleanly without exception
        transcriber.release_vram()
        self.assertIsNone(transcriber.model)

    def test_07_ollama_model_discovery_and_json_cleaning(self):
        """Verify dynamic Ollama model discovery and strict JSON response sanitization."""
        models = get_available_ollama_models()
        self.assertIsInstance(models, list)
        self.assertTrue(len(models) > 0)

        # Test markdown code block extraction
        raw_markdown = "```json\n[{\"title\": \"Epic Clutch\", \"hqs\": 95}]\n```"
        cleaned = clean_json_response(raw_markdown)
        self.assertEqual(cleaned, "[{\"title\": \"Epic Clutch\", \"hqs\": 95}]")

        raw_noisy = "Here are the top moments:\n[{\"start\": 10, \"end\": 25}]\nHope this helps!"
        cleaned_noisy = clean_json_response(raw_noisy)
        self.assertEqual(cleaned_noisy, "[{\"start\": 10, \"end\": 25}]")

    def test_08_api_ai_health_and_models(self):
        """Verify GET /api/ai/health and GET /api/ai/models return valid telemetry."""
        health_res = client.get("/api/ai/health")
        self.assertEqual(health_res.status_code, 200)
        h_data = health_res.json()
        self.assertEqual(h_data.get("status"), "online")
        self.assertIn("modules", h_data)
        self.assertTrue(h_data["modules"].get("audio_intelligence"))
        self.assertTrue(h_data["modules"].get("visual_intelligence"))

        models_res = client.get("/api/ai/models")
        self.assertEqual(models_res.status_code, 200)
        m_data = models_res.json()
        self.assertIn("models", m_data)
        self.assertIn("default", m_data)

    @patch("server.run_ai_scan_task")
    def test_09_api_background_scan_and_polling(self, mock_bg_task):
        """Verify POST /api/ai/scan initiates async job, returns scan_id, and polls stages."""
        # Set active video session first
        sel_res = client.post("/api/sessions/select", json={"filename": "enFF4P7FSg0.mp4"})
        self.assertEqual(sel_res.status_code, 200)

        # Trigger AI scan
        scan_req = {
            "video_path": self.sample_video,
            "num_clips": 2,
            "min_duration": 15,
            "max_duration": 40,
            "scan_start": 5.0,
            "game_type": "generic",
            "whisper_model": "small",
            "ollama_model": "llama3.2:latest",
            "sensitivity": 1.0
        }
        res = client.post("/api/ai/scan", json=scan_req)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("scan_id", data)
        scan_id = data["scan_id"]
        mock_bg_task.assert_called_once()

        # Poll scan status
        poll_res = client.get(f"/api/ai/scan/{scan_id}")
        self.assertEqual(poll_res.status_code, 200)
        p_data = poll_res.json()
        self.assertIn("status", p_data)
        self.assertIn("progress", p_data)
        self.assertIn("stage", p_data)

        # Test scan cancellation
        cancel_res = client.post(f"/api/ai/scan/{scan_id}/cancel")
        self.assertEqual(cancel_res.status_code, 200)
        c_data = cancel_res.json()
        self.assertEqual(c_data.get("status"), "cancelled")

    def test_10_sqlite_clip_moments_persistence(self):
        """Verify clip_moments are persisted in SQLite with HQS, metadata JSON, and can be retrieved."""
        # Create test project
        proj_id = str(uuid.uuid4())
        moment_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO projects (id, name, description, project_state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (proj_id, "AI Highlights Test Proj", "Test", "{}", "2026-10-31T00:00:00Z", "2026-10-31T00:00:00Z"))

            test_meta = {
                "id": moment_id,
                "title": "Insane 1v4 Clutch",
                "hqs": 94.5,
                "hqs_breakdown": {"hook": 24.0, "audio": 19.0, "event": 24.0, "context": 19.0, "visual": 8.5},
                "tags": ["💀 Kill", "⚡ Clutch"]
            }
            cursor.execute("""
            INSERT INTO clip_moments (
                id, project_id, start_time, end_time, category, hook_text, highlight_score, detection_metadata_json, selected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                moment_id,
                proj_id,
                15.0,
                42.0,
                "💀 Kill",
                "WATCH THIS CLUTCH!",
                94.5,
                json.dumps(test_meta),
                1,
                "2026-10-31T00:00:00Z"
            ))

        # Query via API
        res = client.get(f"/api/ai/highlights/{proj_id}")
        self.assertEqual(res.status_code, 200)
        clips = res.json().get("clips", [])
        self.assertEqual(len(clips), 1)
        clip = clips[0]
        self.assertEqual(clip["id"], moment_id)
        self.assertEqual(clip["title"], "Insane 1v4 Clutch")
        self.assertAlmostEqual(clip["hqs"], 94.5, delta=0.1)
        self.assertIn("hqs_breakdown", clip)

        # Update via API
        update_res = client.put(f"/api/ai/highlights/{moment_id}", json={
            "hook_text": "Updated Viral Hook Title",
            "selected": False
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["moment"]["hook_text"], "Updated Viral Hook Title")
        self.assertFalse(update_res.json()["moment"]["selected"])

if __name__ == "__main__":
    unittest.main()
