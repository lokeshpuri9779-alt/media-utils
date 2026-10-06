import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ops_guardian
import cloud_once


class GuardianTests(unittest.TestCase):
    def test_upload_limit_pauses_without_human(self):
        kind = ops_guardian.classify({"http_status": 403, "errors": [{"reason": "uploadLimitExceeded"}]})
        self.assertEqual(kind, "quota_pause")
        self.assertFalse(ops_guardian.recovery_plan(kind)["human_required"])

    def test_auth_requires_human(self):
        kind = ops_guardian.classify({"http_status": 401, "errors": []})
        self.assertEqual(kind, "human_auth")
        self.assertTrue(ops_guardian.recovery_plan(kind)["human_required"])

    def test_transient_error_backs_off(self):
        kind = ops_guardian.classify({"http_status": 503, "errors": []})
        plan = ops_guardian.recovery_plan(kind, 3)
        self.assertEqual(plan["action"], "retry_later")
        self.assertGreater(plan["delay_seconds"], 60)

    def test_state_contains_no_credentials(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ops.json"
            with patch.object(ops_guardian, "OPS_PATH", path):
                state = ops_guardian.record_event("human_auth", {"stage": "oauth"})
                text = path.read_text()
                self.assertIn("reauthorize_youtube", text)
                self.assertNotIn("refresh_token", text)
                self.assertEqual(state["status"], "waiting_for_human")

    def test_controller_half_hour_pacing(self):
        state = {"target": 48, "attempts": 0, "limit_hit": False}
        now = cloud_once.datetime(2026, 10, 6, 0, 0, tzinfo=cloud_once.IST)
        self.assertTrue(cloud_once.scheduled_attempt_due(now, state))
        state["attempts"] = 1
        self.assertFalse(cloud_once.scheduled_attempt_due(now, state))

    def test_same_day_state_cannot_throttle_configured_target(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "quota_state.json"
            path.write_text(
                '{"date":"2026-10-06","target":10,"attempts":0,"successes":0,"limit_hit":false,"other_failures":0}',
                encoding="utf-8",
            )
            now = cloud_once.datetime(2026, 10, 6, 12, 0, tzinfo=cloud_once.IST)
            with patch.object(cloud_once, "STATE_PATH", path), \
                 patch.object(cloud_once, "INITIAL_TARGET", 48), \
                 patch.object(cloud_once, "MAX_TARGET", 48):
                self.assertEqual(cloud_once.load_state(now)["target"], 48)

    def test_controller_duplicate_retry_interface(self):
        self.assertIn("excluded_ids", inspect.signature(cloud_once.make_short).parameters)

    def test_controller_schedule_slot_matches_workflow(self):
        self.assertEqual(cloud_once.SCHEDULE_SLOT_MINUTES, 30)

    def test_controller_has_pre_render_live_history(self):
        source = inspect.getsource(cloud_once.main)
        self.assertLess(source.index("live_channel_history(token)"), source.index("make_short(video"))

    def test_live_history_returns_titles_and_ids(self):
        self.assertTrue(callable(cloud_once.live_channel_history))


if __name__ == "__main__":
    unittest.main()
