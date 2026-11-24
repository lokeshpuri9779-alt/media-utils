"""Fail-closed, idempotent review-only persistence tests."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.performance_short_intake import merge_packets, persist_packet


def item(cid="candidate-a", digest="a" * 64):
    return {
        "candidate_id": cid, "source_sha256": digest,
        "decision": "not_approved", "approved": False,
        "production_ready": False,
        "eligible_for_automatic_publishing": False,
        "published": False,
    }


def packet(*items):
    return {
        "schema_version": 2, "format_profile": "shorts_v2_7scene",
        "count": len(items), "approved_count": 0,
        "rendering_triggered": False, "publication_triggered": False,
        "candidates": list(items),
    }


class PerformanceShortIntakeTests(unittest.TestCase):
    def test_new_candidate_is_persisted_without_promotion(self):
        result = merge_packets({"candidates": []}, packet(item()))
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["candidates"][0]["approved"])
        self.assertFalse(result["candidates"][0]["production_ready"])
        self.assertFalse(result["candidates"][0]["eligible_for_automatic_publishing"])
        self.assertFalse(result["candidates"][0]["published"])
        self.assertFalse(result["rendering_triggered"])
        self.assertFalse(result["publication_triggered"])

    def test_same_candidate_and_same_hash_is_idempotent(self):
        result = merge_packets({"candidates": [item()]}, packet(item()))
        self.assertEqual(result["count"], 1)

    def test_same_id_with_changed_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "source_hash_conflict"):
            merge_packets({"candidates": [item()]}, packet(item(digest="b" * 64)))

    def test_approved_or_ready_item_is_rejected(self):
        promoted = item()
        promoted["approved"] = True
        with self.assertRaisesRegex(ValueError, "remain_unapproved"):
            merge_packets({"candidates": []}, packet(promoted))

    def test_render_or_publish_packet_is_rejected(self):
        unsafe = packet(item())
        unsafe["publication_triggered"] = True
        with self.assertRaisesRegex(ValueError, "review_only"):
            merge_packets({"candidates": []}, unsafe)

    def test_persist_packet_writes_atomically_and_reuses_existing_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review" / "queue.json"
            first = persist_packet(path, packet(item()))
            second = persist_packet(path, packet(item("candidate-b", "b" * 64)))
            self.assertEqual(first["count"], 1)
            self.assertEqual(second["count"], 2)
            restored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([x["candidate_id"] for x in restored["candidates"]],
                             ["candidate-a", "candidate-b"])

    def test_corrupt_existing_queue_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unreadable"):
                persist_packet(path, packet(item()))


if __name__ == "__main__":
    unittest.main()
