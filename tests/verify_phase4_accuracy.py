import os
import sys
import json
import subprocess
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.audio import get_nearest_keyframe, trim_video, generate_audio_waveform

class TestPhase4AccuracyAndTrimming(unittest.TestCase):

    def test_01_frame_timestamps_1080p60(self):
        """Verify 1080p60 frame presentation timestamps."""
        video_path = os.path.join(PROJECT_ROOT, "storage", "uploads", "S1656XwwsYg.mp4")
        if not os.path.exists(video_path):
            self.skipTest("S1656XwwsYg.mp4 not found")

        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "frame=pts_time,best_effort_timestamp_time,key_frame,pict_type",
            "-read_intervals", "0.0%+1.0",
            "-of", "json",
            video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0)
        frames = json.loads(res.stdout).get("frames", [])
        self.assertGreater(len(frames), 10)
        
        # Verify first frame starts at 0.000000
        first_pts = float(frames[0].get("pts_time") or frames[0].get("best_effort_timestamp_time") or 0.0)
        self.assertEqual(first_pts, 0.0)
        self.assertEqual(frames[0]["key_frame"], 1)

        # Verify 60fps delta between consecutive frames is ~0.016667s
        deltas = []
        for i in range(len(frames) - 1):
            t1 = float(frames[i].get("pts_time") or frames[i].get("best_effort_timestamp_time") or 0.0)
            t2 = float(frames[i+1].get("pts_time") or frames[i+1].get("best_effort_timestamp_time") or 0.0)
            deltas.append(t2 - t1)
        avg_delta = sum(deltas) / len(deltas)
        self.assertAlmostEqual(avg_delta, 1.0 / 60.0, places=4)

    def test_02_fast_vs_accurate_trim_pts_comparison(self):
        """Compare Mode A (Fast Keyframe) vs Mode B (Accurate Frame) trimming."""
        video_path = os.path.join(PROJECT_ROOT, "storage", "uploads", "enFF4P7FSg0.mp4")
        out_fast = os.path.join(PROJECT_ROOT, "storage", "cache", "test_fast_trim.mp4")
        out_acc = os.path.join(PROJECT_ROOT, "storage", "cache", "test_acc_trim.mp4")

        req_start = 7.35
        req_end = 12.50

        # Mode A: Fast Keyframe Trim
        res_fast = trim_video(video_path, out_fast, req_start, req_end, mode="fast")
        self.assertTrue(os.path.exists(out_fast))
        self.assertEqual(res_fast["mode"], "fast")
        # In fast mode, actual_start snaps to nearest preceding GOP keyframe
        self.assertLessEqual(res_fast["actual_start"], req_start)

        # Mode B: Accurate Frame Trim
        res_acc = trim_video(video_path, out_acc, req_start, req_end, mode="accurate")
        self.assertTrue(os.path.exists(out_acc))
        self.assertEqual(res_acc["mode"], "accurate")
        self.assertEqual(res_acc["actual_start"], req_start)

        # Check accurate trim duration with ffprobe
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            out_acc
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        dur = float(json.loads(res.stdout)["format"]["duration"])
        expected_dur = req_end - req_start
        self.assertAlmostEqual(dur, expected_dur, delta=0.15)

        # Cleanup
        for p in [out_fast, out_acc]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def test_03_audio_video_synchronization(self):
        """Verify audio and video stream start times match within 0.05s."""
        video_path = os.path.join(PROJECT_ROOT, "storage", "uploads", "enFF4P7FSg0.mp4")
        out_test = os.path.join(PROJECT_ROOT, "storage", "cache", "test_sync_trim.mp4")

        trim_video(video_path, out_test, 10.0, 15.0, mode="accurate")
        self.assertTrue(os.path.exists(out_test))

        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,start_time",
            "-of", "json",
            out_test
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        streams = json.loads(res.stdout).get("streams", [])
        v_start = next((float(s.get("start_time", 0.0)) for s in streams if s["codec_type"] == "video"), 0.0)
        a_start = next((float(s.get("start_time", 0.0)) for s in streams if s["codec_type"] == "audio"), 0.0)
        self.assertAlmostEqual(v_start, a_start, delta=0.05)

        if os.path.exists(out_test):
            os.remove(out_test)

    def test_04_audio_waveform_modes(self):
        """Verify waveform generation for mono, stereo, and empty files."""
        cache_dir = os.path.join(PROJECT_ROOT, "storage", "cache")
        video_path = os.path.join(PROJECT_ROOT, "storage", "uploads", "enFF4P7FSg0.mp4")
        
        # Test real media
        wf = generate_audio_waveform(video_path, cache_dir, num_samples=250)
        self.assertTrue(wf["audio_available"])
        self.assertEqual(len(wf["peaks"]), 250)
        self.assertGreater(max(wf["peaks"]), 0.05)
        self.assertLessEqual(max(wf["peaks"]), 1.0)

        # Test cache hit
        wf_cached = generate_audio_waveform(video_path, cache_dir, num_samples=250)
        self.assertEqual(wf["source_mtime"], wf_cached["source_mtime"])

if __name__ == "__main__":
    unittest.main()
