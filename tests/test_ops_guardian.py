import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ops_guardian


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


if __name__ == "__main__":
    unittest.main()
