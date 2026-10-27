import unittest
from astra_v2.gemini_batch_review import review_batch
from astra_v2.editorial_approval_manifest import story_digest


class ReviewBatchTests(unittest.TestCase):
    def test_rejection_never_exports(self):
        story = {"content_id": "s1", "kind": "microfiction"}
        stories, reviews, audit = review_batch({"status": "unreviewed", "stories": [story]}, [],
            reviewer=lambda s, h: {"approved": False, "record": None, "issues": ["review_failed:HTTP_429"]})
        self.assertEqual(stories["stories"], [])
        self.assertEqual(reviews["reviews"], [])
        self.assertEqual(audit["reviews"][0]["issues"], ["review_failed:HTTP_429"])

    def test_reviewer_receives_authored_candidate(self):
        story = {"content_id": "s1", "kind": "microfiction"}
        observed = []
        def reviewer(candidate, history):
            observed.append(candidate["kind"])
            return {"approved": False, "record": None, "issues": ["editorial_reject"]}
        review_batch({"status": "unreviewed", "stories": [story]}, [], reviewer=reviewer)
        self.assertEqual(observed, ["authored_causal_story"])
        self.assertEqual(story["kind"], "microfiction")

    def test_mismatched_digest_never_exports(self):
        story = {"content_id": "s1", "kind": "microfiction"}
        stories, reviews, audit = review_batch({"status": "unreviewed", "stories": [story]}, [],
            reviewer=lambda s, h: {"approved": True, "record": {"story_sha256": "bad"}, "issues": []})
        self.assertEqual(stories["stories"], [])
        self.assertFalse(audit["reviews"][0]["approved"])


    def test_gemini_review_uses_same_unified_renderer_gate_as_publisher(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        gemini = (root / ".github/workflows/astra-gemini-proposal-batch.yml").read_text()
        publisher = (root / ".github/workflows/astra-v2-publish.yml").read_text()
        preload = (root / ".github/workflows/astra-v2-preload.yml").read_text()
        self.assertIn("ASTRA_UNIFIED_STORY_ENGINE: '1'", publisher)
        dependency_step = gemini.index("      - name: Install CPU-only renderer eligibility dependencies")
        review_start = gemini.index("      - name: Independently review generated proposals")
        self.assertLess(dependency_step, review_start)
        dependencies = gemini[dependency_step:review_start]
        for package in ("httpx==0.28.1", "Pillow==11.3.0",
                        "imageio-ffmpeg==0.6.0", "numpy==2.2.6"):
            self.assertIn(package, dependencies)
        self.assertIn("ASTRA_UNIFIED_STORY_ENGINE: '1'", preload)
        restore = preload.split("      - name: Restore published and reserved IDs", 1)[1].split(
            "      - name:", 1)[0]
        self.assertIn("for f in ai-reviewed-stories.json ai-reviewed-decisions.json", restore)
        self.assertIn('git show "origin/astra-state:$f" > "runtime-health/$f"', restore)
        self.assertIn("Incomplete persistent editorial approval pair", restore)
        self.assertIn("exit 1", restore)
        review_step = gemini.split("      - name: Independently review generated proposals", 1)[1].split(
            "      - name: Persist approved batch to shared ASTRA state", 1)[0]
        self.assertIn("ASTRA_UNIFIED_STORY_ENGINE: '1'", review_step)
        persist_step = gemini.split("      - name: Persist approved batch to shared ASTRA state", 1)[1].split(
            "      - name: Persist Gemini batch diagnostic", 1)[0]
        self.assertIn("ASTRA_UNIFIED_STORY_ENGINE=1 python - <<'PY'", persist_step)
        # The legacy inventory remains intact: only new approvals are screened
        # with the production renderer gate, not retrospectively erased.
        self.assertIn("python -m astra_v2.gemini_inventory_merge", persist_step)

    def test_renderer_incompatible_story_cannot_consume_review_api_or_be_approved(self):
        import os
        from unittest.mock import patch
        from astra_v2.independent_editorial_reviewer import assess
        story = {
            "content_id": "renderer-incompatible-test",
            "title": "The Lighthouse Mystery",
            "kind": "authored_causal_story",
            "genre": "fiction",
            "production_ready": True,
            "plot_fingerprint": "test-lighthouse-unique",
            "story_beats": [
                {"speech": "A keeper watches the lighthouse go dark as a storm moves in.",
                 "visual": "ship", "story_beat": "reveal"},
                {"speech": "The keeper checks the lens and discovers the broken control switch.",
                 "visual": "door", "story_beat": "build"},
                {"speech": "A spare switch is installed before the next wave reaches the shore.",
                 "visual": "robot", "story_beat": "mechanism"},
                {"speech": "The beacon shines again and guides the last boat safely home.",
                 "visual": "ship", "story_beat": "payoff"},
            ],
        }
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), patch(
            "astra_v2.renderer_eligibility.check_renderer_eligibility",
            return_value=(False, "shot 1: human_actor_not_supported_by_directed_icons", ()),
        ):
            verdict = assess(story, [], api_key="unused-test-key",
                             transport=lambda request: self.fail("review API must not be called"))
        self.assertFalse(verdict["approved"])
        self.assertIsNone(verdict["record"])
        self.assertTrue(any("renderer_incompatible" in issue for issue in verdict["issues"]))


if __name__ == "__main__":
    unittest.main()
