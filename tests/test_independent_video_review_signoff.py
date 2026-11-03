"""Offline cryptographic handoff tests. No actual human visual review is asserted."""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from astra_v2.independent_video_review_signoff import sign_independent_review
from astra_v2.semantic_video_gate import evaluate


def digest(data):
    return hashlib.sha256(data).hexdigest()


class IndependentVideoSignoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.candidate = root / "candidate.json"
        self.video = root / "render.mp4"
        self.sheet = root / "contact.jpg"
        self.packet = root / "review.story-review.json"
        self.checklist = root / "completed-checklist.json"
        self.private = root / "reviewer-private.pem"
        self.public = root / "reviewer-public.txt"
        self.output = root / "signed-review.json"
        # Fake fixture bytes only. These tests authenticate bindings and
        # NEVER imply that a real video was visually inspected.
        self.video.write_bytes(b"fictional MP4 bytes -- not a real render")
        self.sheet.write_bytes(b"fictional JPEG bytes -- not a real contact sheet")
        self.story = {
            "content_id": "fiction-qa-id", "title": "The Fox and Clock",
            "genre": "fiction", "format": "short",
            "story_beats": [{
                "speech": f"The fox observes story event {i}.",
                "visual_prompt": f"A fox alongside the clock, event {i}.",
                "story_beat": ("reveal", "build", "twist", "payoff")[i - 1],
            } for i in range(1, 5)],
        }
        self.candidate.write_text(json.dumps(self.story))
        self.packet_data = {
            "schema_version": 1,
            "kind": "independent_story_vs_video_inspection_packet",
            "content_id": self.story["content_id"],
            "title": self.story["title"],
            "story_sha256": "c" * 64,
            "source_mp4_sha256": digest(self.video.read_bytes()),
            "contact_sheet_sha256": digest(self.sheet.read_bytes()),
            "story_beat_count": 4, "frame_sample_count": 4,
            "review_status": "pending_independent_visual_inspection",
            "semantic_quality": "not_verified",
            "publication_approval": False,
            "beats": [
                {"beat": i, "speech": beat["speech"],
                 "visual_prompt": beat["visual_prompt"],
                 "story_beat": beat["story_beat"]}
                for i, beat in enumerate(self.story["story_beats"], 1)
            ],
        }
        self.packet.write_text(json.dumps(self.packet_data))
        self.checks = {
            "complete_video_reviewed": True,
            "beat_checks": [
                {"beat": i, "character_visible": True,
                 "narrated_action_visible": True,
                 "visual_prompt_matches_video": True,
                 "setting_and_prop_continuity": True}
                for i in range(1, 5)
            ],
        }
        self.checklist.write_text(json.dumps(self.checks))
        self.reviewer_key = Ed25519PrivateKey.generate()
        self.private.write_bytes(self.reviewer_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        self.private.chmod(0o600)
        pub = self.reviewer_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public.write_text(base64.b64encode(pub).decode())

    def sign(self, **overrides):
        params = {
            "candidate_path": self.candidate, "packet_path": self.packet,
            "video_path": self.video, "contact_sheet_path": self.sheet,
            "checklist_path": self.checklist,
            "private_key_path": self.private,
            "trusted_public_key_path": self.public,
            "output_path": self.output, "reviewer_id": "human-qa-01",
            "confirm_full_video": True,
        }
        params.update(overrides)
        return sign_independent_review(**params)

    def test_signed_handoff_passes_existing_gate_but_cannot_publish(self):
        result = self.sign()
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["publication_triggered"])
        self.assertFalse(result["publication_approval"])
        decision = json.loads(self.output.read_text())
        self.assertEqual(decision["record"]["content_id"], self.story["content_id"])
        verified = evaluate(self.story, self.video, packet_path=self.packet,
                            review_path=self.output,
                            public_key=self.public.read_text().strip())
        self.assertTrue(verified["verified"])
        self.assertFalse(verified["publication_approval"])
        self.assertFalse(verified["publication_triggered"])
        if os.name == "posix":
            self.assertEqual(self.output.stat().st_mode & 0o077, 0)

    def test_requires_explicit_full_video_confirmation(self):
        for value in (False, None, 1):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, "explicit_full_video_review_confirmation_required"):
                self.sign(confirm_full_video=value)
        self.assertFalse(self.output.exists())

    def test_cannot_sign_incomplete_or_provisional_checklist(self):
        for key in ("character_visible", "narrated_action_visible",
                    "visual_prompt_matches_video", "setting_and_prop_continuity"):
            current = json.loads(json.dumps(self.checks))
            current["beat_checks"][1][key] = False
            self.checklist.write_text(json.dumps(current))
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, "independent_beat_review_incomplete"):
                self.sign()
        self.checks["complete_video_reviewed"] = False
        self.checklist.write_text(json.dumps(self.checks))
        with self.assertRaisesRegex(ValueError, "complete_video_review_not_attested"):
            self.sign()
        self.assertFalse(self.output.exists())

    def test_video_or_sheet_replacement_cannot_be_signed(self):
        self.video.write_bytes(b"changed mp4")
        with self.assertRaisesRegex(ValueError, "hash_mismatch"):
            self.sign()
        self.video.write_bytes(b"fictional MP4 bytes -- not a real render")
        self.sheet.write_bytes(b"tampered sheet")
        with self.assertRaisesRegex(ValueError, "hash_mismatch"):
            self.sign()
        self.assertFalse(self.output.exists())

    def test_changed_video_or_story_after_signing_invalidates_existing_gate(self):
        self.sign()
        self.video.write_bytes(b"new mp4 bytes")
        self.assertEqual(evaluate(self.story, self.video, packet_path=self.packet,
                                  review_path=self.output,
                                  public_key=self.public.read_text())["reason"],
                         "source_media_or_packet_hash_mismatch")
        self.video.write_bytes(b"fictional MP4 bytes -- not a real render")
        self.story["story_beats"][1]["speech"] = "Altered narrated content."
        self.assertEqual(evaluate(self.story, self.video, packet_path=self.packet,
                                  review_path=self.output,
                                  public_key=self.public.read_text())["reason"],
                         "storybeat_payload_mismatch")

    def test_wrong_reviewer_key_cannot_issue_trusted_review(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public.write_text(base64.b64encode(other).decode())
        with self.assertRaisesRegex(ValueError, "reviewer_key_invalid_or_untrusted"):
            self.sign()
        self.assertFalse(self.output.exists())

    def test_rejects_world_readable_private_key(self):
        if os.name != "posix":
            self.skipTest("POSIX key permission check")
        self.private.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "permissions_not_private"):
            self.sign()
        self.assertFalse(self.output.exists())

    def test_missing_or_tampered_story_identity_does_not_sign(self):
        self.story["title"] = "Someone else's story"
        self.candidate.write_text(json.dumps(self.story))
        with self.assertRaisesRegex(ValueError, "review_story_identity_mismatch"):
            self.sign()
        self.assertFalse(self.output.exists())

    def test_review_record_is_never_overwritten(self):
        first = self.sign()
        original = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "review_output_already_exists"):
            self.sign()
        self.assertEqual(self.output.read_bytes(), original)
        self.assertFalse(first["publication_approval"])

    def test_outside_signer_does_not_modify_story_video_or_packet(self):
        originals = {p: p.read_bytes() for p in
                     (self.candidate, self.video, self.sheet, self.packet,
                      self.checklist)}
        self.sign()
        self.assertEqual(originals, {p: p.read_bytes() for p in originals})


if __name__ == "__main__":
    unittest.main()
