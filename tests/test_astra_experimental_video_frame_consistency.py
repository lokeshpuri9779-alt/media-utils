"""Frame-by-frame visual-content checks: different MP4 and PNGs must fail.

In-memory tests deliberately avoid Blender, FFmpeg and GPU requirements.
Production-shaped 384x576/8fps data is checked by the two CPU render jobs.
"""
from __future__ import annotations

import unittest
from tools.experimental_video_frame_consistency import compare_decoded


class EncodedVideoFrameConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.count = 4
        self.size = 12
        self.original = b"".join(
            bytes((r, 40, 80) * 4) for r in (10, 65, 125, 210)
        )

    def test_lossless_sequence_matches(self):
        evidence = compare_decoded(
            self.original, self.original, self.count, frame_bytes=self.size
        )
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["mean_rgb_mae"], 0.0)

    def test_small_h264_like_encoding_noise_allowed(self):
        encoded = bytes(min(255, value + 2) for value in self.original)
        evidence = compare_decoded(
            self.original, encoded, self.count, frame_bytes=self.size
        )
        self.assertTrue(evidence["passed"], evidence)
        self.assertLess(evidence["max_frame_rgb_mae"], 6)

    def test_wrong_order_rejected_even_with_correct_frame_count(self):
        chunks = [
            self.original[i*self.size:(i+1)*self.size]
            for i in range(self.count)
        ]
        swapped = b"".join(reversed(chunks))
        evidence = compare_decoded(
            self.original, swapped, self.count, frame_bytes=self.size
        )
        self.assertFalse(evidence["passed"])
        self.assertFalse(
            evidence["checks"]["every_video_frame_matches_its_png"]
        )

    def test_blank_video_rejected(self):
        evidence = compare_decoded(
            self.original, b"\0" * len(self.original),
            self.count, frame_bytes=self.size
        )
        self.assertFalse(evidence["passed"])

    def test_duplicated_first_frame_rejected(self):
        encoded = self.original[:self.size] * self.count
        self.assertFalse(compare_decoded(
            self.original, encoded, self.count, frame_bytes=self.size
        )["passed"])

    def test_correct_length_wrong_scene_rejected(self):
        second_scene = bytes(255-v for v in self.original)
        self.assertFalse(compare_decoded(
            self.original, second_scene, self.count, frame_bytes=self.size
        )["passed"])

    def test_incomplete_mp4_decode_fails_closed(self):
        with self.assertRaises(ValueError):
            compare_decoded(self.original, self.original[:-1],
                            self.count, frame_bytes=self.size)

    def test_extra_frames_fail_closed(self):
        with self.assertRaises(ValueError):
            compare_decoded(self.original, self.original+b"\0"*self.size,
                            self.count, frame_bytes=self.size)

    def test_corrupt_source_fails_closed(self):
        with self.assertRaises(ValueError):
            compare_decoded(None, self.original, self.count,
                            frame_bytes=self.size)


if __name__ == "__main__":
    unittest.main()
