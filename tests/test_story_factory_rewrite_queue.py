import copy
import unittest
from astra_v2.story_factory_rewrite_queue import rewrite_packet, select_premises


def packet():
    return {"approved_count": 0, "publication_triggered": False,
            "candidates": [{"candidate_id": "c1", "source_sha256": "a" * 64,
                            "review_status": "awaiting_editorial_review",
                            "decision": "not_approved", "production_ready": False,
                            "eligible_for_automatic_publishing": False,
                            "story_beats": ["a", "b", "c", "d"]}]}


class RewriteQueueTests(unittest.TestCase):
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
