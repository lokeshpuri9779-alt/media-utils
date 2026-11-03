"""Offline artifact-pair intake tests: fake media bytes, NO video approval."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

from astra_v2.independent_review_bundle import prepare_review_bundle


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.preload = self.root / "preload.zip"
        self.review = self.root / "review.zip"
        self.output = self.root / "review-ready"
        self.video = b"FAKE_MP4_BYTES_NOT_ACTUAL_REVIEW"
        self.jpg = b"FAKE_JPEG_BYTES_NOT_ACTUAL_REVIEW"
        self.candidate = {
            "content_id": "review-fox-2026", "title": "The Fox in the Forest",
            "genre": "fiction", "format": "short",
            "sha256": digest(self.video),
            "story_beats": [
                {"speech": f"The fox notices change {i}.",
                 "visual_prompt": f"A fox watches the tree at beat {i}.",
                 "story_beat": role}
                for i, role in enumerate(
                    ("reveal", "build", "mechanism", "payoff"), 1)
            ],
        }
        self.packet = {
            "schema_version": 1,
            "kind": "independent_story_vs_video_inspection_packet",
            "content_id": self.candidate["content_id"],
            "title": self.candidate["title"],
            "story_sha256": "a" * 64,
            "source_mp4_sha256": digest(self.video),
            "contact_sheet_sha256": digest(self.jpg),
            "story_beat_count": 4,
            "frame_sample_count": 4,
            "review_status": "pending_independent_visual_inspection",
            "sample_alignment": "planned_storybeat_midpoints",
            "semantic_quality": "not_verified",
            "publication_approval": False,
            "beats": [
                {"beat": i, "speech": beat["speech"],
                 "visual_prompt": beat["visual_prompt"],
                 "story_beat": beat["story_beat"],
                 "contact_sheet_frame_index": i}
                for i, beat in enumerate(self.candidate["story_beats"], 1)
            ],
        }
        self.manifest = {
            "schema_version": 1, "sample_count": 4,
            "source_mp4_sha256": digest(self.video),
            "contact_sheet_sha256": digest(self.jpg),
        }
        self._make_archives()

    def _make_archives(self, *, extra_preload=None, extra_review=None):
        with zipfile.ZipFile(self.preload, "w") as z:
            z.writestr("candidate.json", json.dumps(self.candidate))
            z.writestr("video.mp4", self.video)
            if extra_preload:
                for path, content in extra_preload:
                    z.writestr(path, content)
        with zipfile.ZipFile(self.review, "w") as z:
            z.writestr("other-id-abc.jpg", b"unrelated screenshot")
            z.writestr("other-id-abc.story-review.json", json.dumps({
                **self.packet, "content_id": "unrelated",
            }))
            z.writestr("matching-id-123.jpg", self.jpg)
            z.writestr("matching-id-123.json", json.dumps(self.manifest))
            z.writestr("matching-id-123.story-review.json", json.dumps(self.packet))
            if extra_review:
                for path, content in extra_review:
                    z.writestr(path, content)

    def intake(self):
        return prepare_review_bundle(self.preload, self.review, self.output)

    def test_success_has_false_checklist_and_no_signature(self):
        result = self.intake()
        self.assertTrue(result["artifact_hashes_matched"])
        self.assertEqual(result["semantic_quality"], "not_verified")
        self.assertFalse(result["publication_approval"])
        self.assertFalse(result["publication_triggered"])
        self.assertFalse(result["reviewer_signature_created"])
        self.assertEqual(
            set(p.name for p in self.output.iterdir()), {
                "candidate.json", "video.mp4", "contact.jpg",
                "review.story-review.json", "completed-checklist.json",
                "review-intake-status.json"})
        self.assertEqual((self.output / "video.mp4").read_bytes(), self.video)
        self.assertEqual((self.output / "contact.jpg").read_bytes(), self.jpg)
        check = json.loads((self.output / "completed-checklist.json").read_text())
        self.assertIs(check["complete_video_reviewed"], False)
        self.assertEqual([row["beat"] for row in check["beat_checks"]], [1, 2, 3, 4])
        for row in check["beat_checks"]:
            self.assertTrue(all(val is False for key, val in row.items()
                                if key != "beat"))
        self.assertNotIn("independent-review.json", {p.name for p in self.output.iterdir()})

    def test_malformed_producer_video_hash_rejected(self):
        self.candidate["sha256"] = "a" * 64
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "preload_video_digest_mismatch"):
            self.intake()
        self.assertFalse(self.output.exists())

    def test_mismatched_review_video_hash_rejected(self):
        self.packet["source_mp4_sha256"] = "b" * 64
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "review_provenance_or_digest_mismatch"):
            self.intake()
        self.assertFalse(self.output.exists())

    def test_mismatched_contact_sheet_hash_rejected(self):
        self.packet["contact_sheet_sha256"] = "b" * 64
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "review_provenance_or_digest_mismatch"):
            self.intake()

    def test_mismatched_storybeat_rejected(self):
        self.packet["beats"][2]["speech"] = "Someone else did the action."
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "review_storybeat_payload_mismatch"):
            self.intake()
        self.assertFalse(self.output.exists())

    def test_different_story_cannot_reuse_packet(self):
        self.candidate["content_id"] = "different-fox"
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "review_packet_missing_or_ambiguous"):
            self.intake()

    def test_ambiguous_matching_packets_rejected(self):
        self._make_archives(extra_review=[
            ("another.story-review.json", json.dumps(self.packet)),
        ])
        with self.assertRaisesRegex(ValueError, "review_packet_missing_or_ambiguous"):
            self.intake()

    def test_zip_slip_path_rejected(self):
        self._make_archives(extra_review=[("../evil.json", "{}")])
        with self.assertRaisesRegex(ValueError, "untrusted_or_oversized_review_archive"):
            self.intake()
        self.assertFalse((self.root / "evil.json").exists())

    def test_symlink_inside_zip_rejected(self):
        symlink = zipfile.ZipInfo("link-to-payload")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        self._make_archives(extra_review=[(symlink, "secret-target")])
        with self.assertRaisesRegex(ValueError, "untrusted_or_oversized_review_archive"):
            self.intake()

    def test_unknown_package_member_rejected(self):
        self._make_archives(extra_preload=[("fake-approval.json", "{}")])
        with self.assertRaisesRegex(ValueError, "unexpected_preload_members"):
            self.intake()

    def test_existing_destination_never_overwritten(self):
        self.output.mkdir()
        (self.output / "independent-review.json").write_text("do not replace")
        with self.assertRaisesRegex(ValueError, "review_destination_exists"):
            self.intake()
        self.assertEqual(
            (self.output / "independent-review.json").read_text(), "do not replace")

    def test_no_valid_four_beat_source_rejected(self):
        self.candidate["story_beats"].pop()
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "unsupported_review_candidate"):
            self.intake()

    def test_unsigned_packet_cannot_claim_semantic_approval(self):
        self.packet["semantic_quality"] = "verified"
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "review_provenance_or_digest_mismatch"):
            self.intake()

    def test_review_manifest_sha_must_match_actual_sheet(self):
        self.manifest["contact_sheet_sha256"] = "b" * 64
        self._make_archives()
        with self.assertRaisesRegex(ValueError, "review_provenance_or_digest_mismatch"):
            self.intake()

    def test_archive_duplicate_filename_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self._make_archives(extra_review=[("matching-id-123.jpg", b"other")])
        with self.assertRaisesRegex(ValueError, "untrusted_or_oversized_review_archive"):
            self.intake()


if __name__ == "__main__":
    unittest.main()
