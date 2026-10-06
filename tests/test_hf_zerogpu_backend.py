import unittest
from unittest.mock import patch

import character_video_engine as cve
from video_provider_policy import capability, autonomous_provider_allowed


class ZeroGPUBackendTests(unittest.TestCase):
    def test_zerogpu_policy_is_free_quota(self):
        cap=capability("hf-zerogpu")
        self.assertEqual(cap["cost_class"],"free-quota")
        self.assertTrue(autonomous_provider_allowed("hf-zerogpu"))

    def test_zerogpu_precedes_paid_fallback(self):
        with patch("character_video_engine.open_source_provider_status", return_value={"ready":False,"selected":None}), \
             patch("character_video_engine.remote_status", return_value={"ready":False}), \
             patch("character_video_engine.zerogpu_status", return_value={"ready":True}):
            status=cve.provider_status()
            self.assertEqual(status["selected"],"hf-zerogpu")


if __name__=="__main__":
    unittest.main()
