"""Frame-level negative controls for CPU procedural ASTRA preview renders.

These checks exercise real Pillow pixels but do not claim cinematic quality.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import astra_offline_procedural_preview as preview


class ProceduralPreviewTests(unittest.TestCase):
    def test_all_twelve_shots_change_actual_scene_pixels(self):
        for case in preview.KINDS:
            for stage in range(4):
                with self.subTest(case=case, stage=stage):
                    first = preview.render_frame(case, stage, 0.0)
                    last = preview.render_frame(case, stage, 1.0)
                    self.assertEqual(first.mode, "RGB")
                    self.assertEqual(first.size, (320, 180))
                    count = preview.changed_action_pixels(first, last)
                    self.assertGreaterEqual(count, 64)

    def test_identical_frame_cannot_pass_action_motion_check(self):
        for case in preview.KINDS:
            frame = preview.render_frame(case, 2, 0.3)
            self.assertEqual(preview.changed_action_pixels(frame, frame), 0)

    def test_non_scene_caption_changes_do_not_count(self):
        frame = preview.render_frame(preview.KINDS[0], 1, 0.3)
        changed = frame.copy()
        from PIL import ImageDraw
        ImageDraw.Draw(changed).rectangle((0, 0, 319, 27), fill=(225, 2, 2))
        ImageDraw.Draw(changed).rectangle((0, 161, 319, 179), fill=(2, 2, 225))
        self.assertEqual(preview.changed_action_pixels(frame, changed), 0)

    def test_frame_inputs_fail_closed(self):
        for case, stage, t in [
            ("unknown-case", 0, 0.5),
            (preview.KINDS[0], -1, 0.5),
            (preview.KINDS[0], 4, 0.5),
            (preview.KINDS[0], 0, -0.1),
            (preview.KINDS[0], 0, 1.1),
        ]:
            with self.subTest(case=case, stage=stage, t=t):
                with self.assertRaises(ValueError):
                    preview.render_frame(case, stage, t)

    def test_invalid_image_dimensions_refused(self):
        valid = preview.render_frame(preview.KINDS[0], 0, 0)
        with self.assertRaisesRegex(ValueError, "image format"):
            preview.changed_action_pixels(valid, Image.new("RGB", (10, 10)))

    def test_missing_video_encoder_is_not_simulated(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            preview.shutil, "which", return_value=None
        ):
            with self.assertRaisesRegex(ValueError, "ffmpeg and ffprobe"):
                preview.render_review_videos(Path(tmp))
            self.assertFalse((Path(tmp) / "review-report.json").exists())

    def test_no_production_publishing_symbols_in_preview_module(self):
        # Contract-level defense in depth, not a complete security audit.
        source = Path(preview.__file__).read_text(encoding="utf-8")
        self.assertNotIn("requests.post(", source)
        self.assertNotIn("youtube.upload", source)
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertEqual(preview.TOTAL_FRAMES, preview.FPS * 4)
        self.assertEqual(len(preview.KINDS), 3)


if __name__ == "__main__":
    unittest.main()
