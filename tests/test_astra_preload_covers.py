"""Verify queued video packages remain safe and backwards compatible."""
import unittest
from astra_v2.preload_queue import valid_package_members


class PreloadCoverTests(unittest.TestCase):
    def test_legacy_video_package(self):
        self.assertTrue(valid_package_members(["candidate.json", "video.mp4"]))

    def test_new_cover_package(self):
        self.assertTrue(valid_package_members([
            "candidate.json", "video.mp4", "cover.jpg", "cover_wide.jpg"
        ]))

    def test_reject_missing_video_and_unexpected_files(self):
        self.assertFalse(valid_package_members(["candidate.json", "cover.jpg"]))
        self.assertFalse(valid_package_members([
            "candidate.json", "video.mp4", "../unsafe.jpg"
        ]))
        self.assertFalse(valid_package_members([
            "candidate.json", "video.mp4", "script.py"
        ]))


if __name__ == "__main__":
    unittest.main()
