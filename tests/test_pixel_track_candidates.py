"""Synthetic texture, occlusion, provenance and non-approval tracking tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from astra_v2.pixel_track_candidates import (
    _match_pixels, build_pixel_track_candidates, track_marked_frames,
)
from astra_v2.review_timeline import beat_sample_schedule


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patterned_frame(x=80, y=120, *, decoy=False, visible=True, seed=123):
    arr = np.full((444, 250), 38, dtype=np.uint8)
    texture = np.random.default_rng(seed).integers(
        40, 240, (40, 36), dtype=np.uint8)
    if visible:
        arr[y:y + 40, x:x + 36] = texture
    if decoy:
        arr[120:160, 160:196] = texture
    return Image.fromarray(arr, mode="L")


class PixelMatchingTests(unittest.TestCase):
    def test_small_translation_matches_in_both_directions(self):
        out = _match_pixels(patterned_frame(), patterned_frame(85, 123),
                            (80, 120, 116, 160))
        self.assertEqual(out["status"], "provisional_pixel_match")
        self.assertEqual(out["offset_px"], [5, 3])
        self.assertGreater(out["match_correlation"], .95)
        self.assertGreater(out["nonlocal_margin"], .055)

    def test_featureless_region_abstains(self):
        flat = Image.new("L", (250, 444), 45)
        out = _match_pixels(flat, flat, (80, 120, 116, 160))
        self.assertEqual(out["status"], "low_texture_region")

    def test_repeated_identical_objects_are_ambiguous(self):
        a = patterned_frame(decoy=True)
        b = patterned_frame(x=160, decoy=False)
        out = _match_pixels(a, b, (80, 120, 116, 160))
        self.assertNotEqual(out["status"], "provisional_pixel_match")

    def test_occlusion_abstains(self):
        out = _match_pixels(patterned_frame(), patterned_frame(visible=False),
                            (80, 120, 116, 160))
        self.assertNotEqual(out["status"], "provisional_pixel_match")

    def test_unrelated_texture_abstains(self):
        out = _match_pixels(patterned_frame(),
                            patterned_frame(x=85, seed=987),
                            (80, 120, 116, 160))
        self.assertNotEqual(out["status"], "provisional_pixel_match")

    def test_unrealistic_large_jump_does_not_teleport(self):
        out = _match_pixels(patterned_frame(), patterned_frame(x=135),
                            (80, 120, 116, 160))
        self.assertNotEqual(out["status"], "provisional_pixel_match")

    def test_one_manual_seed_never_leaks_between_beats(self):
        frames = [patterned_frame(80 + (i % 6) * 4, seed=21 + i // 6)
                  for i in range(24)]
        annotation = [{"subject_box": None, "prop_box": None} for _ in range(24)]
        annotation[0]["subject_box"] = (80 / 250, 120 / 444, 116 / 250, 160 / 444)
        tracks = track_marked_frames(frames, annotation)
        self.assertEqual(tracks[0]["subject_box"]["status"], "manual_annotation")
        self.assertEqual(tracks[1]["subject_box"]["status"], "provisional_pixel_match")
        self.assertEqual(tracks[5]["subject_box"]["status"], "provisional_pixel_match")
        self.assertEqual(tracks[6]["subject_box"]["status"],
                         "unavailable_no_reliable_seed")
        self.assertEqual(tracks[0]["prop_box"]["status"],
                         "unavailable_no_reliable_seed")

    def test_later_manual_annotation_restarts_after_occlusion(self):
        frames = [patterned_frame(80 + i * 4) for i in range(6)]
        frames[2] = patterned_frame(visible=False)
        frames.extend([patterned_frame() for _ in range(18)])
        marks = [{"subject_box": None, "prop_box": None} for _ in range(24)]
        start = (80 / 250, 120 / 444, 116 / 250, 160 / 444)
        marks[0]["subject_box"] = start
        marks[3]["subject_box"] = (92 / 250, 120 / 444, 128 / 250, 160 / 444)
        t = track_marked_frames(frames, marks)
        self.assertEqual(t[1]["subject_box"]["status"], "provisional_pixel_match")
        self.assertNotEqual(t[2]["subject_box"]["status"], "provisional_pixel_match")
        self.assertEqual(t[3]["subject_box"]["status"], "manual_annotation")
        self.assertEqual(t[4]["subject_box"]["status"], "provisional_pixel_match")


class ReviewPackagePixelTracksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.video = b"FAKE VIDEO BYTES FOR OFFLINE REGRESSIONS"
        self.candidate = {
            "content_id": "tracked-fox-qa", "title": "Fox and Compass",
            "genre": "fiction", "format": "short", "sha256": sha(self.video),
            "story_beats": [
                {"speech": f"The fox narrates beat {i}.",
                 "visual_prompt": f"The fox stands near a compass in beat {i}.",
                 "story_beat": role}
                for i, role in enumerate(
                    ("reveal", "build", "mechanism", "payoff"), 1)
            ],
        }
        self.packet = {
            "content_id": self.candidate["content_id"],
            "title": self.candidate["title"],
            "source_mp4_sha256": sha(self.video),
            "review_status": "pending_independent_visual_inspection",
            "semantic_quality": "not_verified",
            "publication_approval": False,
            "sample_alignment": "planned_storybeat_midpoints",
            "sample_times_seconds": [3.0, 9.0, 15.0, 21.0],
            "beats": [
                {"beat": i, **b}
                for i, b in enumerate(self.candidate["story_beats"], 1)
            ],
        }
        (self.root / "video.mp4").write_bytes(self.video)
        (self.root / "candidate.json").write_text(json.dumps(self.candidate))
        (self.root / "review.story-review.json").write_text(json.dumps(self.packet))
        from PIL import Image
        sheet = Image.new("RGB", (1500, 1912), "#252525")
        for i in range(24):
            frame = patterned_frame(80 + (i % 6) * 4,
                                    seed=17 + i // 6).convert("RGB")
            sheet.paste(frame, ((i % 6) * 250, (i // 6) * 478 + 34))
        sheet.save(self.root / "timeline-24.jpg", "JPEG", quality=96)
        self.times = beat_sample_schedule(self.packet, 24.0)
        manifest = {
            "kind": "unsigned_review_timeline",
            "content_id": self.candidate["content_id"],
            "source_mp4_sha256": sha(self.video),
            "source_review_packet_sha256":
                sha((self.root / "review.story-review.json").read_bytes()),
            "timeline_jpeg_sha256":
                sha((self.root / "timeline-24.jpg").read_bytes()),
            "sample_count": 24,
            "sample_alignment": "estimated_beat_segments_from_planned_midpoints",
            "frame_times": self.times,
            "semantic_quality": "not_verified",
            "publication_approval": False,
        }
        (self.root / "timeline-24.json").write_text(json.dumps(manifest))
        self.annotation = {
            "schema_version": 1,
            "kind": "unverified_manual_object_region_annotations",
            "content_id": self.candidate["content_id"],
            "source_mp4_sha256": sha(self.video),
            "source_timeline_sha256":
                sha((self.root / "timeline-24.jpg").read_bytes()),
            "coordinates": "normalized_image_content_excluding_34px_headers",
            "frames": [
                {"beat": row["beat"], "frame": i + 1,
                 "time_seconds": row["time_seconds"],
                 "subject_box": ([80 / 250, 120 / 444,
                                  116 / 250, 160 / 444]
                                 if i % 6 == 0 else None),
                 "prop_box": None}
                for i, row in enumerate(self.times)
            ],
            "independent_full_video_review": False,
            "semantic_quality": "not_verified",
            "publication_approval": False,
        }
        self.save_annotation()

    def save_annotation(self):
        (self.root / "object-region-annotations.json").write_text(
            json.dumps(self.annotation))

    def run_builder(self):
        with patch("astra_v2.mp4_motion_evidence._duration",
                   return_value=24.0):
            return build_pixel_track_candidates(self.root)

    def test_bound_report_preserves_inputs_and_never_approves(self):
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        out = self.run_builder()
        self.assertEqual(out["status"], "unsigned_pixel_tracking_candidates_ready")
        self.assertFalse(out["publication_approval"])
        self.assertGreater(out["provisional_matches"], 0)
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        report = json.loads((self.root / "pixel-track-candidates.json").read_text())
        self.assertEqual(report["source_mp4_sha256"], sha(self.video))
        self.assertEqual(len(report["frames"]), 24)
        self.assertTrue(any(x["subject_box"]["status"] ==
                            "provisional_pixel_match" for x in report["frames"]))
        for k in ("complete_video_reviewed", "character_motion_verified",
                  "prop_contact_verified", "publication_approval",
                  "publication_triggered", "reviewer_signature_created"):
            self.assertIs(report[k], False)
        with Image.open(self.root / "pixel-track-overlay.png") as pic:
            self.assertEqual(pic.size, (1500, 1776))

    def test_no_manual_boxes_refuses_to_infer_identity(self):
        for frame in self.annotation["frames"]:
            frame["subject_box"] = None
        self.save_annotation()
        with self.assertRaisesRegex(ValueError, "pixel_tracking_needs_manual_seed"):
            self.run_builder()

    def test_changed_mp4_fails_before_tracking(self):
        (self.root / "video.mp4").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.run_builder()
        self.assertFalse((self.root / "pixel-track-overlay.png").exists())

    def test_tampered_timeline_fails(self):
        (self.root / "timeline-24.jpg").write_bytes(b"tampered timeline")
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.run_builder()

    def test_annotation_bound_to_other_mp4_fails(self):
        self.annotation["source_mp4_sha256"] = "0" * 64
        self.save_annotation()
        with self.assertRaisesRegex(ValueError, "untrusted_pixel_tracking_annotations"):
            self.run_builder()

    def test_forged_human_review_true_fails(self):
        self.annotation["independent_full_video_review"] = True
        self.save_annotation()
        with self.assertRaisesRegex(ValueError, "untrusted_pixel_tracking_annotations"):
            self.run_builder()

    def test_wrong_frame_timestamp_fails(self):
        self.annotation["frames"][1]["time_seconds"] += .1
        self.save_annotation()
        with self.assertRaisesRegex(ValueError, "pixel_tracking_annotation_timing_invalid"):
            self.run_builder()

    def test_invalid_manual_box_fails(self):
        self.annotation["frames"][0]["subject_box"] = [0.1, 0.2, 0.2, float("nan")]
        self.save_annotation()
        with self.assertRaisesRegex(ValueError, "invalid_object_region_box"):
            self.run_builder()

    def test_existing_approval_file_not_overwritten(self):
        path = self.root / "pixel-track-candidates.json"
        path.write_text("already present")
        with self.assertRaisesRegex(ValueError, "pixel_tracking_output_already_exists"):
            self.run_builder()
        self.assertEqual(path.read_text(), "already present")


if __name__ == "__main__":
    unittest.main()
