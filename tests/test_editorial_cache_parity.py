"""Regression checks for indexed editorial and production-supply decisions."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import (
    _semantic_features, _semantic_match_features, editorial_issues,
    semantic_duplicate_match, triage,
)
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.story_supply_review import assess


class EditorialCacheParityTests(unittest.TestCase):
    def test_cached_semantic_evidence_matches_reference(self):
        history = [proposal(i) for i in range(24)]
        features = [(item, _semantic_features(item)) for item in history]
        for i in [0, 4, 15, 23, 30, 51]:
            candidate = proposal(i)
            expected = semantic_duplicate_match(candidate, history)
            actual = _semantic_match_features(
                candidate, _semantic_features(candidate), features, 0.72)
            self.assertEqual(actual, expected)

    def test_cached_editorial_issues_match_reference(self):
        history = [proposal(i) for i in range(20)]
        index = NoveltyIndex(history)
        features = [(item, _semantic_features(item)) for item in history]
        for i in [0, 8, 19, 27, 40]:
            candidate = proposal(i)
            self.assertEqual(
                editorial_issues(candidate, history),
                editorial_issues(candidate, history, novelty_index=index,
                                 semantic_previous=features))

    def test_triage_matches_reference_sequential_decisions(self):
        stories = [proposal(i) for i in range(18)]
        result = triage(stories)
        self.assertEqual(
            len(result["ready_for_review"]) + len(result["needs_work"]),
            len(stories))
        seen = []
        by_id = {item["content_id"]: item
                 for item in result["ready_for_review"] + result["needs_work"]}
        for story in stories:
            item = by_id[story["content_id"]]
            self.assertEqual(item["issues"], editorial_issues(story, seen))
            if "narrative_duplicate" in item["issues"]:
                self.assertEqual(item["novelty_evidence"],
                                 semantic_duplicate_match(story, seen))
            self.assertTrue(item["publication_blocked"])
            seen.append(story)

    def test_supply_audit_keeps_every_proposal_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "proposals.json"
            publisher = Path(folder) / "publisher.json"
            story_history = Path(folder) / "history.json"
            stories = [proposal(i) for i in range(8)]
            ledger.write_text(json.dumps({"proposals": stories}))
            publisher.write_text("{}")
            story_history.write_text("{}")
            result = assess(ledger, publisher, story_history)
            self.assertEqual(result["proposal_count"], len(stories))
            self.assertEqual(result["approved_for_production"], 0)
            self.assertTrue(all(not item["eligible_for_automatic_publishing"]
                                for item in result["proposals"]))


if __name__ == "__main__":
    unittest.main()
