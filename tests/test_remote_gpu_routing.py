import unittest
from unittest.mock import patch
import character_video_engine as cve

class RemoteGPUFallbackTests(unittest.TestCase):
    def test_remote_gpu_is_not_selected_in_agnes_only_mode(self):
        with patch("character_video_engine.agnes_status", return_value={"ready":False}):
            status=cve.provider_status()
            self.assertEqual(status["mode"],"agnes-free-only")
            self.assertIsNone(status["selected"])
            self.assertFalse(status["ready"])

if __name__=="__main__":
    unittest.main()
