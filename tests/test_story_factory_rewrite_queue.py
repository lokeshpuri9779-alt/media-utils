import copy
import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_factory_rewrite_queue import (rewrite_packet, select_premises,
    reusable_pending_queue, rewrite_or_reuse)


def packet():
    return {"approved_count": 0, "publication_triggered": False,
            "candidates": [{"candidate_id": "c1", "source_sha256": "a" * 64,
                            "review_status": "awaiting_editorial_review",
                            "decision": "not_approved", "production_ready": False,
                            "eligible_for_automatic_publishing": False,
                            "story_beats": ["a", "b", "c", "d"]}]}


class RewriteQueueTests(unittest.TestCase):
    def test_pending_unapproved_rewrites_survive_image_quota_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_file = Path(tmp) / "packet.json"
            queue_file = Path(tmp) / "queue.json"
            packet_file.write_text(json.dumps(packet()), encoding="utf-8")
            first, reused = rewrite_or_reuse(packet_file, queue_file, generator=lambda *a, **k: {
                "content_id": "new-story", "title": "New story", "production_ready": True})
            self.assertFalse(reused)
            self.assertTrue(reusable_pending_queue(first))
            original_bytes = queue_file.read_bytes()
            second, reused = rewrite_or_reuse(packet_file, queue_file,
                generator=lambda *a, **k: self.fail("must not consume another Gemini call"),
                reuse_pending=True)
            self.assertTrue(reused)
            self.assertEqual(first, second)
            self.assertEqual(queue_file.read_bytes(), original_bytes)
            self.assertFalse(second["publication_triggered"])
            self.assertEqual(second["approved_count"], 0)

    def test_new_editorial_packet_rotates_queue_with_immutable_image_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_file, queue_file = root / "packet.json", root / "queue.json"
            manifest_file, archive = root / "images.json", root / "archive"
            packet_file.write_text(json.dumps(packet()), encoding="utf-8")
            original, reused = rewrite_or_reuse(packet_file, queue_file,
                generator=lambda *a, **k: {"content_id": "old-story", "title": "Old story"})
            self.assertFalse(reused)
            original_queue_bytes = queue_file.read_bytes()
            manifest_file.write_text(json.dumps({
                "production_ready": False, "assets": [{
                    "story_content_id": "old-story", "path": "sha256/aa/old.png",
                    "approved": False, "production_ready": False}]}), encoding="utf-8")
            original_image_bytes = manifest_file.read_bytes()
            updated = packet()
            updated["candidates"][0]["candidate_id"] = "c2"
            updated["candidates"][0]["source_sha256"] = "b" * 64
            packet_file.write_text(json.dumps(updated), encoding="utf-8")
            replacement, reused = rewrite_or_reuse(packet_file, queue_file,
                generator=lambda *a, **k: {"content_id": "new-story", "title": "New story"},
                reuse_pending=True, archive_dir=archive, image_manifest_path=manifest_file)
            self.assertFalse(reused)
            self.assertEqual(replacement["rewrites"][0]["candidate_id"], "c2")
            self.assertEqual(replacement["rewrites"][0]["story"]["content_id"], "new-story")
            self.assertFalse(replacement["rewrites"][0]["approved"])
            self.assertFalse(replacement["rewrites"][0]["story"]["production_ready"])
            self.assertFalse(replacement["publication_triggered"])
            self.assertEqual(manifest_file.read_bytes(), original_image_bytes)
            archived = list(archive.iterdir())
            self.assertEqual(len(archived), 2)
            self.assertEqual(next(x for x in archived if x.name.endswith(".queue.json")).read_bytes(),
                             original_queue_bytes)
            self.assertEqual(next(x for x in archived if x.name.endswith(".images.json")).read_bytes(),
                             original_image_bytes)

    def test_stale_queue_never_overwritten_without_archive_or_image_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_file, queue_file = root / "packet.json", root / "queue.json"
            packet_file.write_text(json.dumps(packet()), encoding="utf-8")
            rewrite_or_reuse(packet_file, queue_file,
                generator=lambda *a, **k: {"content_id": "old-story", "title": "Old story"})
            old_bytes = queue_file.read_bytes()
            changed = packet()
            changed["candidates"][0]["source_sha256"] = "b" * 64
            packet_file.write_text(json.dumps(changed), encoding="utf-8")
            for archive_dir, image_manifest_path in ((None, None),
                                                      (root / "archive", root / "missing.json")):
                with self.subTest(archive_dir=archive_dir):
                    with self.assertRaises(ValueError):
                        rewrite_or_reuse(packet_file, queue_file,
                            generator=lambda *a, **k: self.fail("no calls without safe archive"),
                            reuse_pending=True, archive_dir=archive_dir,
                            image_manifest_path=image_manifest_path)
                    self.assertEqual(queue_file.read_bytes(), old_bytes)

    def test_stale_queue_refuses_unsafe_image_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_file, queue_file = root / "packet.json", root / "queue.json"
            manifest_file = root / "images.json"
            packet_file.write_text(json.dumps(packet()), encoding="utf-8")
            rewrite_or_reuse(packet_file, queue_file,
                generator=lambda *a, **k: {"content_id": "old-story", "title": "Old story"})
            old_bytes = queue_file.read_bytes()
            changed = packet()
            changed["candidates"][0]["candidate_id"] = "c2"
            packet_file.write_text(json.dumps(changed), encoding="utf-8")
            manifest_file.write_text(json.dumps({"production_ready": True, "assets": []}))
            with self.assertRaisesRegex(ValueError, "unsafe_image_manifest"):
                rewrite_or_reuse(packet_file, queue_file,
                    generator=lambda *a, **k: self.fail("must not generate"),
                    reuse_pending=True, archive_dir=root / "archive",
                    image_manifest_path=manifest_file)
            self.assertEqual(queue_file.read_bytes(), old_bytes)

    def test_unsafe_or_failed_queue_is_never_reused(self):
        safe = rewrite_packet(packet(), generator=lambda *a, **k: {
            "content_id": "new-story", "title": "New story", "production_ready": True})
        for mutation in (
            lambda q: q.update(approved_count=1),
            lambda q: q.update(publication_triggered=True),
            lambda q: q["rewrites"][0].update(approved=True),
            lambda q: q["rewrites"][0]["story"].update(production_ready=True),
            lambda q: q["rewrites"][0].update(status="rewrite_failed"),
        ):
            with self.subTest(mutation=mutation):
                invalid = copy.deepcopy(safe)
                mutation(invalid)
                self.assertFalse(reusable_pending_queue(invalid))
        with tempfile.TemporaryDirectory() as tmp:
            packet_file = Path(tmp) / "packet.json"
            queue_file = Path(tmp) / "queue.json"
            packet_file.write_text(json.dumps(packet()), encoding="utf-8")
            invalid = copy.deepcopy(safe)
            invalid["rewrites"][0]["story"]["production_ready"] = True
            queue_file.write_text(json.dumps(invalid), encoding="utf-8")
            result, reused = rewrite_or_reuse(packet_file, queue_file,
                generator=lambda *a, **k: {"content_id": "replacement", "title": "Safe replacement"},
                reuse_pending=True)
            self.assertFalse(reused)
            self.assertFalse(result["rewrites"][0]["story"]["production_ready"])
            self.assertEqual(result["rewrites"][0]["story"]["content_id"], "replacement")

    def test_rewrite_is_not_approved_or_production_ready(self):
        result = rewrite_packet(packet(), generator=lambda *a, **k: {"content_id": "new-1", "title": "New story", "production_ready": True})
        self.assertEqual(result["approved_count"], 0)
        self.assertFalse(result["rewrites"][0]["story"]["production_ready"])
        self.assertFalse(result["rewrites"][0]["approved"])

    def test_missing_identity_is_rejected(self):
        result = rewrite_packet(packet(), generator=lambda *a, **k: {"title": "Missing ID"})
        self.assertEqual(result["rewrites"][0]["status"], "rewrite_failed")

    def test_repeated_plot_requests_new_mechanism_without_reusing_beats(self):
        p = packet()
        candidate = p["candidates"][0]
        candidate.update(review_status="needs_new_plot",
                         review_issues=["repeated_underlying_plot_mechanism"],
                         title="Rejected old title")
        original = copy.deepcopy(p)
        calls = []
        def generate(*args, premise):
            calls.append(premise)
            self.assertEqual(premise["story_beats"], [])
            self.assertNotEqual(premise["title"], candidate["title"])
            self.assertEqual(premise["required_next_action"], "invent_distinct_causal_plot_mechanism")
            return {"content_id": "new-plot", "title": "Entirely new story", "production_ready": True}
        result = rewrite_packet(p, generator=generate)
        self.assertEqual(len(calls), 1)
        self.assertEqual(p, original)
        self.assertEqual(result["selected_for_rewrite"], 1)
        self.assertIsNone(result["blocked_reason"])
        self.assertEqual(result["available_premises"]["needs_new_plot"], 1)
        self.assertFalse(result["publication_triggered"])
        self.assertEqual(result["approved_count"], 0)
        row = result["rewrites"][0]
        self.assertEqual(row["status"], "awaiting_independent_editorial_approval")
        self.assertFalse(row["approved"])
        self.assertFalse(row["story"]["production_ready"])

    def test_new_plot_requires_repeated_mechanism_rejection_and_safe_flags(self):
        for changes in ({"review_issues": []}, {"decision": "approved"},
                        {"production_ready": True}, {"eligible_for_automatic_publishing": True}):
            with self.subTest(changes=changes):
                p = packet()
                p["candidates"][0].update(review_status="needs_new_plot",
                    review_issues=["repeated_underlying_plot_mechanism"])
                p["candidates"][0].update(changes)
                result = rewrite_packet(p, generator=lambda *a, **k: self.fail("should not generate"))
                self.assertEqual(result["selected_for_rewrite"], 0)
                self.assertEqual(result["blocked_reason"], "no_unique_premises")

    def test_new_plot_request_cannot_reuse_prior_identity(self):
        p = packet()
        p["candidates"][0].update(review_status="needs_new_plot",
            review_issues=["repeated_underlying_plot_mechanism"])
        old = {"content_id": "published", "title": "Published story"}
        for generated in (old, {"content_id": "new-id", "title": " PUBLISHED STORY "}):
            with self.subTest(generated=generated):
                result = rewrite_packet(p, prior=[old], generator=lambda *a, **k: generated)
                self.assertEqual(result["rewrites"][0]["status"], "rewrite_failed")
                self.assertFalse(result["rewrites"][0]["approved"])
                self.assertFalse(result["publication_triggered"])

    def test_rejected_packet_fails_closed(self):
        p = packet()
        p["approved_count"] = 1
        with self.assertRaises(ValueError):
            select_premises(p)

    def test_failed_generation_stays_review_only(self):
        def fail(*args, **kwargs):
            raise ValueError("invalid")
        result = rewrite_packet(packet(), generator=fail)
        self.assertEqual(result["rewrites"][0]["status"], "rewrite_failed")
        self.assertEqual(result["approved_count"], 0)


if __name__ == "__main__":
    unittest.main()
