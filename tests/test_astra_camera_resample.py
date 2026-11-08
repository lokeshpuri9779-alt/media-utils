"""Opt-in ASTRA Studio camera resizing: unchanged default and safe dimensions."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw, ImageStat
from astra_v2.camera_resample import camera_resample


class StudioCameraResizeTests(unittest.TestCase):
    def test_default_is_existing_bicubic(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(camera_resample(), Image.Resampling.BICUBIC)

    def test_only_explicit_opt_in_enables_bilinear(self):
        for value in ("", "yes", "TRUE", "2"):
            with self.subTest(value=value), patch.dict(os.environ, {"ASTRA_FAST_CAMERA_RESAMPLE": value}):
                self.assertEqual(camera_resample(), Image.Resampling.BICUBIC)
        with patch.dict(os.environ, {"ASTRA_FAST_CAMERA_RESAMPLE": "1"}):
            self.assertEqual(camera_resample(), Image.Resampling.BILINEAR)

    def test_small_camera_zoom_has_low_mean_visual_difference(self):
        # Deterministic proxy only. It is not a substitute for real MP4/scene QA.
        source = Image.new("RGB", (180, 320), (24, 48, 78))
        draw = ImageDraw.Draw(source)
        for y in range(8, 320, 19):
            draw.line([(0, y), (179, min(319, y+30))], fill=(180, 205, 220), width=2)
        draw.rectangle((42, 80, 145, 220), outline=(250, 228, 72), width=4)
        results = []
        for mode in (Image.Resampling.BICUBIC, Image.Resampling.BILINEAR):
            enlarged = source.resize((184, 328), mode)
            results.append(enlarged.crop((2, 4, 182, 324)))
        self.assertEqual(results[0].size, source.size)
        self.assertEqual(results[1].size, source.size)
        diff = ImageStat.Stat(ImageChops.difference(*results))
        self.assertLess(max(diff.mean), 4.0)


if __name__ == "__main__":
    unittest.main()
