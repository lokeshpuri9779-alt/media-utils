"""Runway probe negative controls: reports cannot confer publishing status."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import unittest

from tools.astra_live_publisher_runway import audit, main


class LiveRunwayTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, 12, 45, tzinfo=timezone.utc)
        self.stories = [{"content_id": f"candidate-{i}",
                         "title": f"Independent candidate {i}"} for i in range(3)]
        self.state = {
            "version": 2, "day": "2026-11-04", "confirmed_today": 3,
            "published": {"old": {"video_id": "test-video"}},
            "pending": {"pending-id": {"content_id": "pending-candidate"}},
            "reserved": {},
            "last_workflow_result": {
                "at": "2026-11-04T08:26:00+00:00", "outcome": "processing"},
        }
        self.batch = {"observed_at": "2026-11-04T12:41:00+00:00",
                      "generated": 18, "approved": 3}
        self.pair = {"stories": self.stories}
        self.decisions = {"reviews": [
            {"content_id": s["content_id"], "decision": "approve"}
            for s in self.stories
        ]}

    def test_stale_journal_distinguished_from_actual_scheduler_status(self):
        observed = []
        def validator(stories, reviews, history):
            observed.append((stories, reviews, history))
            return {"results": [
                {"content_id": "candidate-0", "approved": False,
                 "issues": ["publication_renderer_incompatible: unknown prop"]},
                {"content_id": "candidate-1", "approved": True, "issues": []},
                {"content_id": "candidate-2", "approved": True, "issues": []},
            ], "approved_count": 2}
        report = audit(self.state, self.pair, self.decisions, self.batch,
                       [{"content_id": "known"}], now=self.now,
                       validator=validator)
        self.assertEqual(len(observed), 1)
        self.assertEqual(report["publisher_checkpoint_status"],
                         "stale_stored_checkpoint")
        self.assertEqual(report["confirmed_today_in_stored_journal"], 3)
        self.assertEqual(report["pending_processing_in_stored_journal"], 1)
        self.assertEqual(report["current_intake_eligible"], 2)
        self.assertEqual(report["current_intake_blocked"], 1)
        self.assertEqual(report["current_intake_blocking_categories"],
                         {"publication_": 1})
        self.assertFalse(report["recent_persisted_story_intake"][0]["intake_eligible"])
        for name in ("publication_triggered", "automatic_approval",
                     "paid_provider_called", "production_route_modified"):
            self.assertFalse(report[name])
        self.assertTrue(report["technical_intake_is_not_visual_approval"])

    def test_recent_checkpoint_is_not_publication_evidence(self):
        self.state["last_workflow_result"]["at"] = "2026-11-04T12:44:00+00:00"
        report = audit(self.state, self.pair, self.decisions, self.batch, [],
                       now=self.now, validator=lambda stories, reviews, history:
                       {"results": [{"content_id": s["content_id"],
                                     "approved": False, "issues": ["narrative_duplicate"]}
                                    for s in stories], "approved_count": 0})
        self.assertEqual(report["publisher_checkpoint_status"],
                         "recent_stored_checkpoint")
        self.assertEqual(report["current_intake_eligible"], 0)
        self.assertFalse(report["publication_triggered"])

    def test_invalid_sources_and_forged_intake_fail_closed(self):
        valid = lambda stories, reviews, history: {
            "results": [{"content_id": s["content_id"],
                         "approved": True, "issues": []} for s in stories],
            "approved_count": len(stories)}
        for changes in (
            {"version": 1},
            {"published": []},
            {"pending": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                audit({**self.state, **changes}, self.pair, self.decisions,
                      self.batch, [], now=self.now, validator=valid)
        with self.assertRaises(ValueError):
            audit(self.state, {"stories": []}, {"reviews": []}, self.batch,
                  [], now=self.now, validator=lambda *args: {
                      "results": [], "approved_count": 2})
        with self.assertRaises(ValueError):
            audit(self.state, self.pair, self.decisions, self.batch,
                  [], now=self.now, validator=lambda *args: {
                      "results": [{"content_id": "forged", "approved": True,
                                   "issues": []}] * 3, "approved_count": 3})

    def test_missing_protected_ledgers_do_not_generate_fake_runway(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            with self.assertRaises(SystemExit):
                main(["--state-dir", tmp, "--output", str(out)])
            self.assertFalse(out.exists())

    def test_missing_timestamp_does_not_claim_healthy_scheduler(self):
        self.state.pop("last_workflow_result")
        report = audit(self.state, self.pair, self.decisions, self.batch, [],
                       now=self.now, validator=lambda stories, reviews, _: {
                           "results": [{"content_id": s["content_id"],
                                        "approved": False, "issues": ["not_production_ready"]}
                                       for s in stories], "approved_count": 0})
        self.assertEqual(report["publisher_checkpoint_status"],
                         "unknown_missing_checkpoint")
        self.assertIsNone(report["publisher_checkpoint_age_minutes"])


if __name__ == "__main__":
    unittest.main()
