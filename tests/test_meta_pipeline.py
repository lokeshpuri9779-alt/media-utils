"""Unit tests for the local ASTRA Meta processing controller."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_pipeline import run

class MetaPipelineControllerTests(unittest.TestCase):
    def test_controller_runs_all_optional_stages(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = root / "story.json"
            manifest.write_text('{"scenes":[{"prompt":"scene"}]}')
            soundtrack = root / "music.wav"
            srt = root / "captions.srt"
            soundtrack.write_bytes(b"test")
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
            def fake_assemble(_manifest, _clips, output):
                output.write_bytes(b"assembled")
            def fake_audio(_video, _audio, output):
                output.write_bytes(b"mixed")
            def fake_caption(_video, _srt, output):
                output.write_bytes(b"captioned")
            with patch("integrations.meta_pipeline.assemble", side_effect=fake_assemble), \
                 patch("integrations.meta_pipeline.add_soundtrack", side_effect=fake_audio), \
                 patch("integrations.meta_pipeline.caption", side_effect=fake_caption), \
                 patch("integrations.meta_pipeline.validate", return_value={"ready": True, "errors": []}):
                result = run(manifest, root / "clips", root / "output", soundtrack, srt)
            self.assertTrue(result["ready"])
            self.assertFalse(result["published"])
            self.assertEqual((root / "output/final.mp4").read_bytes(), b"captioned")

    def test_rejected_gate_remains_unpublished(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch("integrations.meta_pipeline.assemble", side_effect=lambda _a, _b, output: output.write_bytes(b"fake")), \
                 patch("integrations.meta_pipeline.validate", return_value={"ready": False, "errors": ["Audio missing"]}):
                result = run(root / "story.json", root / "clips", root / "output")
            self.assertFalse(result["ready"])
            self.assertFalse(result["published"])

if __name__ == "__main__":
    unittest.main()
