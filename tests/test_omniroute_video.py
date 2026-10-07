import os
import sys
import unittest
from unittest.mock import Mock, patch
import omniroute_video as video


class VideoPolicyTests(unittest.TestCase):
    def test_no_local_gpu(self):
        self.assertFalse(video.policy()["local_gpu_required"])

    def test_no_paid_fallback(self):
        self.assertFalse(video.policy()["paid_fallback"])

    def test_private_quality_gate(self):
        p = video.policy()
        self.assertTrue(p["private_canary"] and p["quality_gate_required"])

    def test_unverified_routes_never_submit(self):
        transport = Mock()
        with patch.dict(os.environ, {"OMNIROUTE_BASE_URL": "https://gateway.example/v1",
                                    "ASTRA_ALLOW_PAID_VIDEO": "false"}), \
             patch.dict(sys.modules, {"requests": transport}):
            for model in ("provider/premium", "provider/free"):
                with self.subTest(model=model), self.assertRaisesRegex(
                        RuntimeError, "zero_cost_video_route_not_verified"):
                    video.generate_video("A short animation", model)
        transport.post.assert_not_called()

    def test_missing_endpoint_is_reported(self):
        with patch.dict(os.environ, {}, clear=True):
            result = video.readiness("provider/model")
        self.assertIn("omniroute_endpoint_not_configured", result["blockers"])
        self.assertFalse(result["generation_attempted"])

    def test_paid_flag_cannot_bypass_guard(self):
        with patch.dict(os.environ, {"ASTRA_ALLOW_PAID_VIDEO": "true"}):
            with self.assertRaisesRegex(RuntimeError, "Paid video remains disabled"):
                video.generate_video("test", "provider/model")

    def test_missing_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            video.generate_video("test", "auto")
