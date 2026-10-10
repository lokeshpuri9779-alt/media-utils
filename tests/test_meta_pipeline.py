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

    def test_rejected_gate_deletes_final_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "output"
            output.mkdir()
            (output / "final.mp4").write_bytes(b"old-publishable-video")
            with patch("integrations.meta_pipeline.assemble", side_effect=lambda _a, _b, dest: dest.write_bytes(b"new-bad-video")), \
                 patch("integrations.meta_pipeline.validate", return_value={"ready": False, "errors": ["Bad media"]}):
                result = run(root / "story.json", root / "clips", output)
            self.assertFalse(result["ready"])
            self.assertFalse((output / "final.mp4").exists())

    def test_processing_exception_clears_stale_output_and_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "output"
            output.mkdir()
            (output / "final.mp4").write_bytes(b"stale")
            (output / "handoff.json").write_text('{"ready":true}')
            def fail(_manifest, _clips, destination):
                destination.write_bytes(b"incomplete")
                raise RuntimeError("encoder crashed")
            with patch("integrations.meta_pipeline.assemble", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "encoder crashed"):
                    run(root / "story.json", root / "clips", output)
            self.assertFalse((output / "final.mp4").exists())
            self.assertFalse((output / "handoff.json").exists())

    def test_retry_removes_all_stale_intermediates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "output"
            output.mkdir()
            for name in ("assembled.mp4", "mixed.mp4", "captioned.mp4", "final.mp4"):
                (output / name).write_bytes(b"old")
            def fail_before_render(_manifest, _clips, _destination):
                raise RuntimeError("render unavailable")
            with patch("integrations.meta_pipeline.assemble", side_effect=fail_before_render):
                with self.assertRaisesRegex(RuntimeError, "render unavailable"):
                    run(root / "story.json", root / "clips", output)
            for name in ("assembled.mp4", "mixed.mp4", "captioned.mp4", "final.mp4"):
                self.assertFalse((output / name).exists(), name)

if __name__ == "__main__":
    unittest.main()
