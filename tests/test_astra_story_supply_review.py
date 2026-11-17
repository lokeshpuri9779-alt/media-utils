import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_supply_review import assess
from astra_v2.causal_premise_review import CausalPremiseIndex
from astra_v2.story_editorial import triage


class SupplyReviewTests(unittest.TestCase):
    def test_drafts_remain_blocked_even_when_ledger_exists(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "proposals.json"
            ledger.write_text(json.dumps({"proposals": [proposal(0), proposal(1)]}))
            result = assess(ledger, Path(root) / "missing-publisher.json",
                            Path(root) / "missing-stories.json")
            self.assertEqual(result["proposal_count"], 2)
            self.assertEqual(result["approved_for_production"], 0)
            self.assertEqual(result["publication_blocked_count"], 2)
            self.assertTrue(all(not x["eligible_for_automatic_publishing"]
                                for x in result["proposals"]))

    def test_review_queue_contains_only_editorial_only_candidates(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "proposals.json"
            ledger.write_text(json.dumps({"proposals": [proposal(i) for i in range(12)]}))
            result = assess(ledger, Path(root) / "missing-publisher.json",
                            Path(root) / "missing-stories.json")
            expected = [entry for entry in result["proposals"]
                        if entry["editorial_issues"] == ["human_or_model_editorial_review_required"]]
            self.assertEqual(result["review_queue"], expected)
            self.assertEqual(len(result["review_queue"]),
                             result["structurally_sound_unreviewed_count"])
            self.assertTrue(all(not entry["eligible_for_automatic_publishing"]
                                for entry in result["review_queue"]))
            self.assertEqual(result["approved_for_production"], 0)

    def test_indexed_audit_matches_reference_editorial_issues(self):
        from astra_v2.story_editorial import editorial_issues, _semantic_features
        from astra_v2.proposal_novelty_index import NoveltyIndex
        with tempfile.TemporaryDirectory() as root:
            candidates = [proposal(i) for i in range(18)]
            candidates.append(dict(candidates[0], content_id="repeat-story"))
            ledger = Path(root) / "ledger.json"
            ledger.write_text(json.dumps({"proposals": candidates}))
            result = assess(ledger, Path(root) / "missing-publisher.json",
                            Path(root) / "missing-stories.json")
            history = []
            novelty = NoveltyIndex()
            semantic = []
            expected = []
            for story in candidates:
                expected.append(editorial_issues(
                    story, history, novelty_index=novelty, semantic_previous=semantic))
                history.append(story)
                novelty.add(story)
                semantic.append((story, _semantic_features(story)))
            self.assertEqual(
                [entry["editorial_issues"] for entry in result["proposals"]], expected)
            self.assertEqual(result["approved_for_production"], 0)

    def test_causal_index_preserves_first_historical_match(self):
        from astra_v2.causal_premise_review import causal_premise_match
        first = {"content_id": "first", "central_conflict": "blocked bridge",
                 "decisive_choice": "share supplies", "resolution": "bridge repaired"}
        second = dict(first, content_id="second")
        candidate = dict(first, content_id="candidate")
        index = CausalPremiseIndex([first, second])
        self.assertEqual(index.match(candidate), causal_premise_match(candidate, [first, second]))
        self.assertEqual(index.match(candidate)["matched_content_id"], "first")

    def test_triage_indexes_causal_arcs_across_same_batch(self):
        first = proposal(0)
        second = proposal(1)
        arc = {
            "central_conflict": "blocked bridge isolates the village",
            "decisive_choice": "share limited repair supplies",
            "resolution": "neighbors rebuild the bridge together",
        }
        first.update(arc)
        second.update(arc)
        second["content_id"] = "same-batch-causal-repeat"
        result = triage([first, second], use_semantic_index=True)
        repeated = [item for item in result["needs_work"]
                    if item["content_id"] == "same-batch-causal-repeat"]
        self.assertEqual(len(repeated), 1)
        self.assertIn("repeated_causal_premise", repeated[0]["issues"])
        self.assertFalse(repeated[0]["publication_blocked"] is False and
                         repeated[0].get("publication_approved", False))

    def test_published_fingerprint_is_flagged(self):
        with tempfile.TemporaryDirectory() as root:
            candidate = proposal(0)
            ledger = Path(root) / "ledger.json"
            publisher = Path(root) / "publisher.json"
            ledger.write_text(json.dumps({"proposals": [candidate]}))
            publisher.write_text(json.dumps({"published": {"previous": {
                "plot_fingerprint": candidate["plot_fingerprint"]}}}))
            result = assess(ledger, publisher, Path(root) / "missing.json")
            self.assertIn("narrative_duplicate", result["proposals"][0]["editorial_issues"])


if __name__ == "__main__":
    unittest.main()