import os
import sys
import json
import unittest
from io import BytesIO
from unittest.mock import patch

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from server import app, sanitize_filename, get_safe_storage_path, validate_remote_url, UPLOAD_DIR
from core.system_monitor import get_real_system_metrics

class TestPhase2SecurityAndTelemetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_system_metrics_endpoint(self):
        """Verify GET /api/system/metrics returns genuine real metrics structure."""
        res = self.client.get("/api/system/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        # Verify CPU metrics
        self.assertIn("cpu", data)
        self.assertIn("cores", data["cpu"])
        self.assertIn("threads", data["cpu"])
        self.assertIn("util_pct", data["cpu"])
        self.assertGreater(data["cpu"]["cores"], 0)
        
        # Verify RAM metrics
        self.assertIn("ram", data)
        self.assertIn("total_gb", data["ram"])
        self.assertIn("used_gb", data["ram"])
        self.assertIn("free_gb", data["ram"])
        self.assertGreater(data["ram"]["total_gb"], 0)

        # Verify Disk metrics
        self.assertIn("disk", data)
        self.assertIn("free_gb", data["disk"])
        self.assertGreater(data["disk"]["total_gb"], 0)

        # Verify GPU metrics
        self.assertIn("gpu", data)
        self.assertIn("available", data["gpu"])
        self.assertIn("nvenc_supported", data["gpu"])
        self.assertIn("cuda_available", data["gpu"])
        print(f"  [PASS] System Metrics: CPU {data['cpu']['util_pct']}%, RAM {data['ram']['used_gb']}/{data['ram']['total_gb']}GB, GPU: {data['gpu']['name']} ({data['gpu']['status']})")

    def test_02_gpu_unavailable_handling(self):
        """Verify system monitor handles missing or failing nvidia-smi safely without crashing."""
        with patch("subprocess.run", side_effect=FileNotFoundError("nvidia-smi not found")):
            # Clear cache
            from core.system_monitor import _metrics_cache
            _metrics_cache["timestamp"] = 0.0
            metrics = get_real_system_metrics()
            self.assertFalse(metrics["gpu"]["available"])
            self.assertEqual(metrics["gpu"]["status"], "unavailable")
            self.assertIn("not found", metrics["gpu"]["error"])
            print("  [PASS] GPU unavailable fallback handled gracefully without crash")

    def test_03_path_traversal_sanitization(self):
        """Verify path traversal attacks like ../../windows are blocked and sanitized."""
        dangerous_names = [
            "../../etc/passwd",
            "..\\..\\Windows\\System32\\cmd.exe",
            "....//....//boot.ini",
            "/absolute/root/file.mp4"
        ]
        for name in dangerous_names:
            safe = sanitize_filename(name)
            # Should have no path separators
            self.assertNotIn("/", safe)
            self.assertNotIn("\\", safe)
            # Should not start with ..
            self.assertFalse(safe.startswith(".."))
            
            # get_safe_storage_path must stay within UPLOAD_DIR
            resolved = get_safe_storage_path(safe, UPLOAD_DIR)
            self.assertTrue(resolved.startswith(os.path.abspath(UPLOAD_DIR)))
        print("  [PASS] Path traversal sanitization strictly enforced")

    def test_04_session_select_traversal_rejection(self):
        """Verify POST /api/sessions/select rejects traversal payload."""
        # Malicious payload trying to select outside uploads
        res = self.client.post("/api/sessions/select", json={"filename": "../../Windows/System32/notepad.exe"})
        # Should be rejected with 400 or 404 (file not found in uploads)
        self.assertIn(res.status_code, [400, 404])
        print("  [PASS] Session select directory traversal rejected")

    def test_05_remote_url_ssrf_rejection(self):
        """Verify validate_remote_url blocks SSRF attempts to private networks and non-video schemes."""
        dangerous_urls = [
            "http://127.0.0.1:8000/api/secret",
            "http://localhost:8080/admin",
            "http://192.168.1.1/router",
            "http://169.254.169.254/metadata",
            "file:///etc/passwd",
            "ftp://files.example.com",
            "http://evil-malicious-site.com/exploit.mp4"
        ]
        for url in dangerous_urls:
            with self.assertRaises(Exception) as ctx:
                validate_remote_url(url)
            self.assertTrue(ctx.exception.status_code == 400)
        print("  [PASS] Remote URL SSRF protection verified")

    def test_06_remote_url_valid_providers(self):
        """Verify legitimate YouTube and Twitch URLs are accepted."""
        valid_urls = [
            "https://www.youtube.com/watch?v=S1656XwwsYg",
            "https://youtu.be/S1656XwwsYg",
            "https://www.twitch.tv/videos/123456789"
        ]
        for url in valid_urls:
            res = validate_remote_url(url)
            self.assertEqual(res, url)
        print("  [PASS] Legitimate YouTube & Twitch URLs validated correctly")

    def test_07_cors_allowed_and_disallowed_origins(self):
        """Verify CORS allows localhost:5173 / tauri and rejects unauthorized remote origins."""
        # Allowed origin
        res_allowed = self.client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
        )
        self.assertEqual(res_allowed.status_code, 200)
        self.assertEqual(res_allowed.headers.get("access-control-allow-origin"), "http://localhost:5173")

        # Disallowed external origin
        res_disallowed = self.client.options(
            "/api/health",
            headers={"Origin": "http://malicious-external-site.com", "Access-Control-Request-Method": "GET"}
        )
        self.assertNotEqual(res_disallowed.headers.get("access-control-allow-origin"), "http://malicious-external-site.com")
        print("  [PASS] CORS restricted to local development & desktop Tauri origins")

    def test_08_file_upload_validation(self):
        """Verify upload endpoint validates extension, sanitizes traversal, and rejects corrupt media."""
        # 1. Invalid extension rejected
        dummy_txt = BytesIO(b"Hello world executable")
        res_bad = self.client.post(
            "/api/import/upload",
            files={"file": ("malicious.exe", dummy_txt, "application/octet-stream")}
        )
        self.assertEqual(res_bad.status_code, 400)
        self.assertIn("Unsupported format", res_bad.json()["detail"])

        # 2. Corrupt media payload properly detected and rejected with 400
        dummy_corrupt = BytesIO(b"\x00\x00\x00\x18ftypmp42corruptdata")
        res_corrupt = self.client.post(
            "/api/import/upload",
            files={"file": ("../../corrupt_test_clip.mp4", dummy_corrupt, "video/mp4")}
        )
        self.assertEqual(res_corrupt.status_code, 400)
        self.assertIn("Corrupt or invalid video", res_corrupt.json()["detail"])
        # Ensure corrupt file was purged from disk
        self.assertFalse(os.path.exists(os.path.join(UPLOAD_DIR, "corrupt_test_clip.mp4")))

        # 3. Valid video upload: read first 256KB of an existing real video in uploads
        existing = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".mp4")]
        if existing:
            with open(os.path.join(UPLOAD_DIR, existing[0]), "rb") as real_f:
                real_bytes = real_f.read(512 * 1024)
            res_valid = self.client.post(
                "/api/import/upload",
                files={"file": ("../../valid_traversal_test.mp4", BytesIO(real_bytes), "video/mp4")}
            )
            # Traversal must be stripped into UPLOAD_DIR
            self.assertFalse(os.path.exists(os.path.join(UPLOAD_DIR, "..", "valid_traversal_test.mp4")))
            safe_target = os.path.join(UPLOAD_DIR, "valid_traversal_test.mp4")
            if os.path.exists(safe_target):
                os.remove(safe_target)

        print("  [PASS] File upload security & corrupt media validation verified")

    def test_09_local_sessions_and_library(self):
        """Verify local sessions and library list endpoints work properly."""
        res_local = self.client.get("/api/sessions/local")
        self.assertEqual(res_local.status_code, 200)
        self.assertIsInstance(res_local.json(), list)

        res_lib = self.client.get("/api/library")
        self.assertEqual(res_lib.status_code, 200)
        self.assertIsInstance(res_lib.json(), list)
        print(f"  [PASS] Existing local sessions ({len(res_local.json())}) and library shorts ({len(res_lib.json())}) preserved")

if __name__ == "__main__":
    unittest.main()
