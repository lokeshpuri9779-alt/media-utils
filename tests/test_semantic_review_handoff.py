"""Offline Git transport regressions; synthetic fixtures do NOT prove visuals."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from astra_v2.independent_video_review_signoff import sign_independent_review
from astra_v2.semantic_review_handoff import restore_review
from astra_v2.semantic_video_gate import evaluate


def sha(content):
    return hashlib.sha256(content).hexdigest()


def git(*args):
    return subprocess.run(["git", *map(str, args)], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=20).stdout.strip()


class SignedReviewRestorationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.root = root
        self.video = root / "test.mp4"
        self.sheet = root / "contact.jpg"
        self.packet = root / "packet.json"
        self.candidate = root / "candidate.json"
        self.signed = root / "signed-review.json"
        self.checklist = root / "checklist.json"
        self.key = root / "reviewer.pem"
        self.public = root / "reviewer-public.txt"
        self.video.write_bytes(b"FAKE test MP4 bytes, no actual visual inspection")
        self.sheet.write_bytes(b"FAKE test JPEG bytes, no actual visual inspection")
        story = {
            "genre": "fiction", "format": "short",
            "content_id": "unique-fox-story", "title": "The Fox and the River",
            "story_beats": [
                {"speech": f"The fox narrates event {i}.",
                 "visual_prompt": f"A fox near the river at step {i}.",
                 "story_beat": phase}
                for i, phase in enumerate(("reveal", "build", "twist", "payoff"), 1)
            ],
        }
        self.story = story
        self.candidate.write_text(json.dumps(story))
        self.packet.write_text(json.dumps({
            "schema_version": 1,
            "kind": "independent_story_vs_video_inspection_packet",
            "content_id": story["content_id"], "title": story["title"],
            "story_sha256": "a" * 64,
            "source_mp4_sha256": sha(self.video.read_bytes()),
            "contact_sheet_sha256": sha(self.sheet.read_bytes()),
            "story_beat_count": 4, "frame_sample_count": 4,
            "review_status": "pending_independent_visual_inspection",
            "semantic_quality": "not_verified", "publication_approval": False,
            "beats": [
                {"beat": i, "speech": beat["speech"],
                 "visual_prompt": beat["visual_prompt"],
                 "story_beat": beat["story_beat"]}
                for i, beat in enumerate(story["story_beats"], 1)
            ],
        }))
        self.checklist.write_text(json.dumps({
            "complete_video_reviewed": True,
            "beat_checks": [
                {"beat": i, "character_visible": True,
                 "narrated_action_visible": True,
                 "visual_prompt_matches_video": True,
                 "setting_and_prop_continuity": True} for i in range(1, 5)
            ],
        }))
        key = Ed25519PrivateKey.generate()
        self.key.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        self.key.chmod(0o600)
        self.public.write_text(base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode())
        sign_independent_review(
            candidate_path=self.candidate, packet_path=self.packet,
            video_path=self.video, contact_sheet_path=self.sheet,
            checklist_path=self.checklist, private_key_path=self.key,
            trusted_public_key_path=self.public, output_path=self.signed,
            reviewer_id="test-human-reviewer", confirm_full_video=True)
        self.repo = root / "checkout"
        self.repo.mkdir()
        self.remote = root / "remote.git"
        git("init", "--bare", self.remote)
        git("init", "-b", "main", self.repo)
        git("-C", self.repo, "config", "user.name", "Test Reviewer")
        git("-C", self.repo, "config", "user.email", "test-reviewer@example.invalid")
        git("-C", self.repo, "remote", "add", "origin", self.remote)
        (self.repo / "README.md").write_text("Local test checkout, not a review.")
        git("-C", self.repo, "add", "README.md")
        git("-C", self.repo, "commit", "-m", "local test base")
        self.destination = root / "restored"

    def stage(self, *, packet=None, decision=None, omit_decision=False):
        git("-C", self.repo, "checkout", "--orphan", "astra-video-reviews")
        git("-C", self.repo, "rm", "-rf", ".")
        key = sha(self.story["content_id"].encode())
        movie = sha(self.video.read_bytes())
        directory = self.repo / "signed-reviews" / key / movie
        directory.mkdir(parents=True)
        (directory / "packet.json").write_bytes(
            self.packet.read_bytes() if packet is None else packet)
        if not omit_decision:
            (directory / "signed-review.json").write_bytes(
                self.signed.read_bytes() if decision is None else decision)
        git("-C", self.repo, "add", ".")
        git("-C", self.repo, "commit", "-m", "independent fake signed review test fixture")
        git("-C", self.repo, "push", "origin", "astra-video-reviews")
        git("-C", self.repo, "checkout", "main")

    def restore(self, *, story=None, video=None, public_key=None):
        return restore_review(
            self.story if story is None else story,
            self.video if video is None else video,
            self.destination, self.public.read_text() if public_key is None else public_key,
            repo_dir=self.repo)

    def test_valid_review_restores_exact_signed_pair_but_cannot_publish(self):
        self.stage()
        result = self.restore()
        self.assertTrue(result["verified"])
        self.assertEqual(result["reason"], "independent_attestation_verified")
        self.assertFalse(result["publication_approval"])
        self.assertFalse(result["publication_triggered"])
        self.assertEqual(Path(result["packet_path"]).read_bytes(), self.packet.read_bytes())
        self.assertEqual(Path(result["decision_path"]).read_bytes(), self.signed.read_bytes())
        self.assertEqual(evaluate(self.story, self.video,
                                 packet_path=result["packet_path"],
                                 review_path=result["decision_path"],
                                 public_key=self.public.read_text())["verified"], True)

    def test_absent_branch_stays_unverified(self):
        self.assertEqual(self.restore()["reason"], "review_branch_unavailable")
        self.assertFalse(self.destination.exists())

    def test_missing_decision_is_not_a_signed_review(self):
        self.stage(omit_decision=True)
        self.assertEqual(self.restore()["reason"], "matching_signed_review_missing_or_invalid")
        self.assertFalse(self.destination.exists())

    def test_tampered_signature_fails_and_discards_runner_documents(self):
        invalid = json.loads(self.signed.read_text())
        invalid["record"]["reviewer_id"] = "malicious"
        self.stage(decision=json.dumps(invalid).encode())
        result = self.restore()
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "review_signature_invalid")
        self.assertFalse((self.destination / "packet.json").exists())
        self.assertFalse((self.destination / "signed-review.json").exists())

    def test_tampered_packet_fails_and_discards_runner_documents(self):
        packet = json.loads(self.packet.read_text())
        packet["beats"][2]["speech"] = "Altered after the human review"
        self.stage(packet=json.dumps(packet).encode())
        result = self.restore()
        self.assertFalse(result["verified"])
        self.assertIn(result["reason"], {
            "storybeat_payload_mismatch", "source_media_or_packet_hash_mismatch"})
        self.assertFalse((self.destination / "signed-review.json").exists())

    def test_changed_video_cannot_reuse_prior_review(self):
        self.stage()
        self.video.write_bytes(b"Different encoded bytes")
        result = self.restore()
        self.assertEqual(result["reason"], "matching_signed_review_missing_or_invalid")
        self.assertFalse(result["verified"])

    def test_changed_content_id_cannot_reuse_review(self):
        self.stage()
        changed = {**self.story, "content_id": "different"}
        result = self.restore(story=changed)
        self.assertEqual(result["reason"], "matching_signed_review_missing_or_invalid")

    def test_wrong_public_key_rejected(self):
        self.stage()
        different = Ed25519PrivateKey.generate()
        different_pub = base64.b64encode(different.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        result = self.restore(public_key=different_pub)
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "review_signature_invalid")

    def test_oversized_signed_blob_is_not_accepted(self):
        self.stage(decision=b"x" * (64 * 1024 + 1))
        result = self.restore()
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "matching_signed_review_missing_or_invalid")
        self.assertFalse((self.destination / "signed-review.json").exists())

    def test_missing_key_prevents_transport_fetch(self):
        with patch("astra_v2.semantic_review_handoff._git",
                   side_effect=AssertionError("must not fetch without public key")):
            self.assertEqual(self.restore(public_key="")["reason"],
                             "trusted_reviewer_public_key_unavailable")

    def test_gate_does_not_fetch_without_existing_mandatory_switch(self):
        with patch.dict(os.environ, {"ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW": "0"}):
            with patch("astra_v2.semantic_review_handoff.restore_review",
                       side_effect=AssertionError("unexpected Git fetch")):
                result = evaluate(self.story, self.video, public_key=self.public.read_text())
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "review_missing")

    def test_mandatory_gate_restores_and_verifies_review_before_upload(self):
        self.stage()
        from astra_v2.semantic_review_handoff import restore_review as genuine
        def in_local_checkout(candidate, video_path, output_dir, public_key):
            return genuine(candidate, video_path, output_dir, public_key,
                           repo_dir=self.repo)
        with patch.dict(os.environ, {"ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW": "1"}):
            with patch("astra_v2.semantic_review_handoff.restore_review",
                       side_effect=in_local_checkout):
                result = evaluate(self.story, self.video, public_key=self.public.read_text())
        self.assertTrue(result["verified"])
        self.assertFalse(result["publication_approval"])

    def test_mandatory_gate_missing_evidence_never_claims_approval(self):
        with patch.dict(os.environ, {"ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW": "1"}):
            with patch("astra_v2.semantic_review_handoff.restore_review",
                       return_value={"reason": "matching_signed_review_missing_or_invalid",
                                     "verified": False}):
                result = evaluate(self.story, self.video, public_key=self.public.read_text())
        self.assertFalse(result["verified"])
        self.assertFalse(result["publication_approval"])
        self.assertFalse(result["publication_triggered"])


if __name__ == "__main__":
    unittest.main()
