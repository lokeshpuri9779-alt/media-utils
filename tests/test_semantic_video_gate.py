"""Offline security regressions: independent FULL-MP4 sign-off, never generator approval."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from astra_v2.semantic_video_gate import evaluate, _canonical



def example_story():
    return {
        "content_id": "qa-story-one", "title": "The Fox Repairs a Clock",
        "genre": "fiction", "format": "short",
        "story_beats": [
            {"speech": f"The fox investigates problem {n}.",
             "visual_prompt": f"Fox and clock, phase {n}.", "story_beat": phase}
            for n, phase in enumerate(("reveal", "build", "twist", "payoff"), 1)
        ],
    }


def packet_for(candidate, video_hash):
    return {
        "schema_version": 1,
        "kind": "independent_story_vs_video_inspection_packet",
        "content_id": candidate["content_id"],
        "title": candidate["title"],
        "story_sha256": "c" * 64,
        "source_mp4_sha256": video_hash,
        "contact_sheet_sha256": "d" * 64,
        "story_beat_count": 4, "frame_sample_count": 4,
        "review_status": "pending_independent_visual_inspection",
        "semantic_quality": "not_verified", "publication_approval": False,
        "beats": [
            {"beat": n, "speech": beat["speech"],
             "visual_prompt": beat["visual_prompt"],
             "story_beat": beat["story_beat"],
             "contact_sheet_frame_index": n}
            for n, beat in enumerate(candidate["story_beats"], 1)
        ],
    }


class SemanticVideoGateTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        raw = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public_key = base64.b64encode(raw).decode("ascii")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.video = self.root / "video.mp4"
        self.video.write_bytes(b"fictional-test-video-bytes-no-network")
        self.candidate = example_story()
        self.packet_path = self.root / "story-review.json"
        self.review_path = self.root / "independent-review.json"
        self.packet = packet_for(self.candidate,
                                 hashlib.sha256(self.video.read_bytes()).hexdigest())
        self._write_packet()
        self.record = {
            "schema_version": 1,
            "content_id": self.candidate["content_id"],
            "story_sha256": self.packet["story_sha256"],
            "source_mp4_sha256": self.packet["source_mp4_sha256"],
            "contact_sheet_sha256": self.packet["contact_sheet_sha256"],
            "review_packet_sha256": hashlib.sha256(self.packet_path.read_bytes()).hexdigest(),
            "reviewer_id": "independent-human-qa",
            "reviewed_at": "2026-11-02T19:30:00+00:00",
            "decision": "approve", "complete_video_reviewed": True,
            "beat_checks": [
                {"beat": i, "character_visible": True,
                 "narrated_action_visible": True,
                 "visual_prompt_matches_video": True,
                 "setting_and_prop_continuity": True}
                for i in range(1, 5)
            ],
        }
        self._sign()

    def _write_packet(self):
        self.packet_path.write_text(json.dumps(self.packet, sort_keys=True))

    def _sign(self):
        tag = base64.b64encode(self.private_key.sign(
            _canonical(self.record))).decode("ascii")
        self.review_path.write_text(
            json.dumps({"record": self.record, "signature_ed25519": tag}))

    def assess(self, **kwargs):
        return evaluate(self.candidate, self.video,
                        packet_path=kwargs.get("packet_path", self.packet_path),
                        review_path=kwargs.get("review_path", self.review_path),
                        public_key=kwargs.get("public_key", self.public_key))

    def test_authenticated_full_video_attestation_is_not_publication_approval(self):
        result = self.assess()
        self.assertTrue(result["verified"])
        self.assertEqual(result["reason"], "independent_attestation_verified")
        self.assertFalse(result["publication_approval"])
        self.assertFalse(result["publication_triggered"])

    def test_without_review_or_key_fails_closed(self):
        self.assertEqual(self.assess(review_path="")["reason"], "review_missing")
        self.assertEqual(self.assess(public_key="")["reason"],
                         "trusted_reviewer_public_key_unavailable")
        other_key = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.assertEqual(self.assess(public_key=base64.b64encode(other_key).decode())["reason"],
                         "review_signature_invalid")

    def test_actual_video_bytes_must_match_reviewed_hash(self):
        self.video.write_bytes(b"replacement-encoded-mp4-bytes")
        self.assertEqual(self.assess()["reason"],
                         "source_media_or_packet_hash_mismatch")

    def test_packet_replacement_cannot_reuse_review_signature(self):
        self.packet["beats"][0]["speech"] = "substituted narration"
        self._write_packet()
        self.assertIn(self.assess()["reason"],
                      ("storybeat_payload_mismatch",
                       "source_media_or_packet_hash_mismatch"))

    def test_candidate_script_change_cannot_reuse_review(self):
        self.candidate["story_beats"][0]["speech"] = "A different event happened."
        self.assertEqual(self.assess()["reason"], "storybeat_payload_mismatch")

    def test_unauthorized_change_even_with_forged_record_rejected(self):
        payload = json.loads(self.review_path.read_text())
        payload["record"]["decision"] = "reject"
        self.review_path.write_text(json.dumps(payload))
        self.assertEqual(self.assess()["reason"], "review_signature_invalid")

    def test_incomplete_review_never_approves_even_with_signature(self):
        modifications = (
            ("complete_video_reviewed", False, "full_video_review_not_approved"),
            ("decision", "reject", "full_video_review_not_approved"),
        )
        for field, value, reason in modifications:
            with self.subTest(field=field):
                before = self.record[field]
                self.record[field] = value
                self._sign()
                self.assertEqual(self.assess()["reason"], reason)
                self.record[field] = before
        self._sign()
        self.record["beat_checks"][1]["narrated_action_visible"] = False
        self._sign()
        self.assertEqual(self.assess()["reason"], "visual_checks_incomplete")

    def test_no_automatic_signature_or_unsigned_packet_approval(self):
        self.review_path.unlink()
        self.assertFalse(self.assess()["verified"])
        self.assertEqual(self.assess()["reason"], "review_evidence_unavailable")
        self.assertEqual(self.packet["semantic_quality"], "not_verified")
        self.assertFalse(self.packet["publication_approval"])

    def test_untrusted_schema_and_unaligned_stories_fail_closed(self):
        self.record["beat_checks"] = self.record["beat_checks"][:3]
        self._sign()
        self.assertEqual(self.assess()["reason"], "visual_checks_incomplete")
        self.record["beat_checks"].append(
            {"beat": 4, "character_visible": True, "narrated_action_visible": True,
             "visual_prompt_matches_video": True, "setting_and_prop_continuity": True})
        self.record["reviewed_at"] = "2026-11-02"
        self._sign()
        self.assertEqual(self.assess()["reason"], "review_time_invalid")
        self.record["reviewed_at"] = "2026-11-02T19:30:00+00:00"
        self.record["beat_checks"][0]["character_visible"] = 1
        self._sign()
        self.assertEqual(self.assess()["reason"], "visual_checks_incomplete")

    def test_final_upload_interlock_is_before_reservation(self):
        source = (Path(__file__).resolve().parents[1] / "astra_v2/run.py").read_text()
        gate = source.index("ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW")
        reservation = source.index('state.setdefault("reserved", {})[cid] = {')
        upload = source.index("video_id = youtube.upload(")
        self.assertLess(gate, reservation)
        self.assertLess(reservation, upload)
        self.assertIn('if review_required and not verification["verified"]:', source)
        self.assertIn('outcome="quality_skip"', source)
        self.assertIn('reason="semantic_video_review_"', source)
        # No review secret is passed to the provider or stored in state.
        self.assertNotIn('state["semantic_review_key"]', source)


if __name__ == "__main__":
    unittest.main()
