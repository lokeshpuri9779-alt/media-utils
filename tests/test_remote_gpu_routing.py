import os
import unittest
from unittest.mock import patch

import character_video_engine as cve


class RemoteGPUFallbackTests(unittest.TestCase):
    def test_remote_open_source_precedes_paid(self):
        with patch("character_video_engine.open_source_provider_status", return_value={"ready":False,"selected":None}),              patch("character_video_engine.remote_status", return_value={"ready":True}),              patch.dict(os.environ, {"REPLICATE_API_TOKEN":"token","ASTRA_ALLOW_PAID_CHARACTER_VIDEO":"1"}, clear=True):
            status=cve.provider_status()
            self.assertEqual(status["selected"],"remote-open-source-gpu")

    def test_paid_not_ready_when_remote_missing_and_flag_off(self):
        with patch("character_video_engine.open_source_provider_status", return_value={"ready":False,"selected":None}),              patch("character_video_engine.remote_status", return_value={"ready":False}),              patch.dict(os.environ, {"REPLICATE_API_TOKEN":"token"}, clear=True):
            status=cve.provider_status()
            self.assertFalse(status["ready"])


if __name__=="__main__":
    unittest.main()
