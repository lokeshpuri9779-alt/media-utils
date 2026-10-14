"""Verify opt-in Pillow shadow adapter without changing production defaults."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.pillow_engine1_adapter import pillow_enabled, render_shadow_preview

class PillowAdapterTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(pillow_enabled())
            self.assertEqual(render_shadow_preview("/tmp/not-rendered.mp4")["status"], "disabled")

    def test_shadow_preview_does_not_publish(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/"preview.mp4"
            with patch.dict(os.environ, {"ASTRA_ENGINE1_PILLOW":"1"}):
                result=render_shadow_preview(target,duration=0.5,fps=8)
            self.assertEqual(result["status"],"rendered")
            self.assertFalse(result["publishable"])
            self.assertGreater(target.stat().st_size,0)

if __name__=="__main__":
    unittest.main()
