import os
import unittest
from unittest.mock import patch

import open_source_video_engine as oss
import character_video_engine as cve


class OpenSourceVideoRouterTests(unittest.TestCase):
    def test_no_gpu_worker_is_not_ready(self):
        with patch("open_source_video_engine.gpu_available", return_value=False),              patch.dict(os.environ, {}, clear=True):
            status=oss.provider_status()
            self.assertFalse(status["ready"])
            self.assertIsNone(status["selected"])

    def test_ltx_has_priority_over_wan(self):
        with patch("open_source_video_engine.ltx_status", return_value={"ready":True,"provider":"ltx-local"}),              patch("open_source_video_engine.wan_status", return_value={"ready":True,"provider":"wan2.2-local"}),              patch.dict(os.environ, {}, clear=True):
            self.assertEqual(oss.provider_status()["selected"],"ltx-local")

    def test_paid_fallback_stays_disabled_without_explicit_flag(self):
        with patch("character_video_engine.open_source_provider_status", return_value={"ready":False,"selected":None}),              patch.dict(os.environ, {"REPLICATE_API_TOKEN":"token"}, clear=True):
            status=cve.provider_status()
            self.assertFalse(status["ready"])
            self.assertFalse(status["paid_fallback"]["paid_generation_enabled"])


if __name__=="__main__":
    unittest.main()
