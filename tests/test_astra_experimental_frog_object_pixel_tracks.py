"""Unit and adversarial tests for fixed-scene frog object-colored pixel tracks.

Synthetic RGB fixtures isolate the algorithm from Blender/FFmpeg installation.
The CPU story workflow separately tests the same code on real rendered frames.
"""
import unittest

from tools.experimental_frog_object_pixel_tracks import (
    SIZE, W, gold_region_center, pale_region_left, seed_brown_center,
    SEED_ROIS, POT_SOIL_ROI, score, negative_controls,
)


def synthetic():
    frames = [bytearray(SIZE) for _ in range(32)]
    positions = [317, 261, 209, 164, 125]
    airplane_left_edges = [81, 91, 111, 130, 157, 179, 199, 212, 217]

    def fill(frame, left, top, width, height, rgb):
        for y in range(top, top + height):
            for x in range(left, left + width):
                k = 3 * (y * W + x)
                frame[k:k+3] = bytes(rgb)

    for i, x in enumerate(positions, start=8):
        fill(frames[i], x - 7, 319, 15, 10, (200, 130, 30))
    for i, x in enumerate(airplane_left_edges, start=13):
        fill(frames[i], x, 289, 20, 7, (208, 194, 161))
    for i, x, y in ((22, 90, 282), (23, 112, 285),
                    (24, 168, 286), (25, 223, 298)):
        fill(frames[i], x - 9, y - 5, 18, 10, (112, 82, 62))
    for i, width, height in ((29, 9, 16), (30, 14, 16), (31, 40, 48)):
        fill(frames[i], 240, 242, width, height, (20, 180, 34))
    l, top, right, bottom = POT_SOIL_ROI
    for i in range(22, 26):
        fill(frames[i], l, top, right - l, bottom - top, (50, 50, 45))

    report = {
        "success": True,
        "editorial_review_required": True,
        "semantic_quality": "not_verified",
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "frames": [{"frame": i,
                    "phase": "rescue" if 8 <= i <= 21 else "other",
                    "camera_xyz": [0, -5.3, 3.1]}
                   for i in range(32)],
    }
    return frames, report


class FixedActorPixelTracks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames, cls.report = synthetic()

    def test_clean_object_trajectories_and_sprout_pass(self):
        r = score(self.frames, self.report)
        self.assertTrue(r["passed"], r)
        self.assertEqual(len(r["checks"]), 9)
        self.assertTrue(all(r["checks"].values()))
        self.assertEqual(r["semantic_quality"], "not_verified")
        self.assertFalse(r["production_ready"])

    def test_individual_color_detector_coordinates(self):
        self.assertEqual(gold_region_center(self.frames[8])["center_x"], 317)
        self.assertEqual(pale_region_left(self.frames[21])["left_x"], 217)
        self.assertEqual(seed_brown_center(
            self.frames[24], SEED_ROIS[24])["center_x"], 167.5)

    def test_ten_corrupted_sequences_rejected(self):
        result = negative_controls(self.frames, self.report)
        self.assertEqual(result["negative_case_count"], 10)
        self.assertTrue(result["all_corruptions_rejected"], result)
        self.assertEqual(result["semantic_quality"], "not_verified")

    def test_paper_plane_moving_backward_rejected(self):
        frames = self.frames.copy()
        frames[19] = frames[13]
        r = score(frames, self.report)
        self.assertFalse(r["passed"])
        self.assertIn("paper_region_moves_right_after_contact",
                      r["failed_checks"])

    def test_early_sprout_rejected_with_unchanged_report(self):
        frames = self.frames.copy()
        frames[28] = frames[31]
        r = score(frames, self.report)
        self.assertFalse(r["passed"])
        self.assertIn("sprout_pixels_follow_seed_transfer", r["failed_checks"])

    def test_seed_trajectory_reversal_rejected(self):
        frames = self.frames.copy()
        frames[25] = frames[22]
        r = score(frames, self.report)
        self.assertFalse(r["passed"])
        self.assertIn("seed_pixel_path_advances_toward_pot", r["failed_checks"])

    def test_erased_seed_rejected(self):
        frames = self.frames.copy()
        frames[24] = bytes(SIZE)
        r = score(frames, self.report)
        self.assertFalse(r["passed"])
        self.assertIn("seed_brown_blob_before_soil", r["failed_checks"])

    def test_pot_soil_not_mistaken_for_rewound_seed(self):
        # In the real render frame 22 the pot's brown pixels occupy x>=240
        # within the old frame-25 ROI. The seed itself remains at x~90.
        frames = self.frames.copy()
        frames[22] = bytearray(self.frames[22])
        for y in range(292, 327):
            for x in range(240, 251):
                k = 3 * (y * W + x)
                frames[22][k:k+3] = bytes((112, 82, 62))
        frames[25] = frames[22]
        r = score(frames, self.report)
        self.assertFalse(r["passed"])
        self.assertIn("seed_pixel_path_advances_toward_pot",
                      r["failed_checks"])

    def test_seed_color_matching_soil_rejected(self):
        frames = self.frames.copy()
        frames[25] = bytearray(self.frames[25])
        l, top, right, bottom = POT_SOIL_ROI
        for y in range(top, bottom):
            for x in range(l, right):
                k = 3 * (y * W + x)
                frames[25][k:k + 3] = bytes((86, 86, 86))
        result = score(frames, self.report)
        self.assertFalse(result["passed"])
        self.assertIn("seed_visibly_contrasts_with_pot_soil",
                      result["failed_checks"])

    def test_metadata_cannot_claim_publication(self):
        for key in ("approved", "published", "production_ready",
                    "paid_apis_used"):
            report = dict(self.report)
            report[key] = True
            with self.subTest(flag=key):
                r = score(self.frames, report)
                self.assertFalse(r["passed"])

    def test_camera_cut_disables_fixed_scene_proxy(self):
        report = dict(self.report)
        report["frames"] = [dict(x) for x in self.report["frames"]]
        report["frames"][17]["camera_xyz"] = [3, -1, 7]
        self.assertFalse(score(self.frames, report)["passed"])

    def test_wrong_rgb_frame_size_rejected(self):
        with self.assertRaises(ValueError):
            gold_region_center(bytes(20))
        with self.assertRaises(ValueError):
            pale_region_left(bytes(20))

    def test_missing_frame_fails_closed(self):
        self.assertFalse(score(self.frames[:-1], self.report)["passed"])


if __name__ == "__main__":
    unittest.main()
