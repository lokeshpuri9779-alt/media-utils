import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agnes_free_video as agnes
import character_video_engine as cve


class AgnesBackendTests(unittest.TestCase):
    def test_status_requires_key(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(agnes.agnes_status()["ready"])
        with patch.dict(os.environ,{"AGNES_API_KEY":"x"},clear=True):
            self.assertTrue(agnes.agnes_status()["ready"])

    def test_character_engine_selects_only_agnes(self):
        with patch("character_video_engine.agnes_status", return_value={"ready":True}):
            status=cve.provider_status()
            self.assertEqual(status["mode"],"agnes-free-only")
            self.assertEqual(status["selected"],"agnes-free-video")

    def test_frame_config_is_vertical_safe_and_capped(self):
        frames,fps=agnes._frame_config(5)
        self.assertEqual(fps,24)
        self.assertLessEqual(frames,121)
        self.assertEqual((frames-1)%8,0)


if __name__=="__main__":
    unittest.main()
