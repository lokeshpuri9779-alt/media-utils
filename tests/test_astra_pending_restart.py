"""Regression: pending YouTube uploads survive publisher process restarts."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from astra_v2.control import read_json, state_for_day, write_json
from astra_v2.run import reconcile


class PendingRestartTests(unittest.TestCase):
    def test_pending_to_published_across_two_state_restores(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "publisher-state.json"
            state = state_for_day()
            day = state["day"]
            state["pending"]["video-restart-1"] = {
                "content_id": "story-restart-1",
                "day": day,
                "title": "A New Story",
                "format": "short",
                "uploaded_at": state["created_at"],
            }
            write_json(path, state)

            # A new scheduled run restores the state but YouTube is still processing.
            first = state_for_day(read_json(path))
            youtube = Mock()
            youtube.status.return_value = {
                "privacyStatus": "public", "uploadStatus": "uploaded"
            }
            self.assertEqual(reconcile(youtube, first), [])
            self.assertIn("video-restart-1", first["pending"])
            self.assertEqual(first["confirmed_today"], 0)
            write_json(path, first)

            # Another scheduled run sees YouTube's final processing result.
            second = state_for_day(read_json(path))
            youtube.status.return_value = {
                "privacyStatus": "public", "uploadStatus": "processed"
            }
            legacy = SimpleNamespace(CONTENT_META={}, record_video=Mock())
            with patch.dict("sys.modules", {"cloud_once": legacy}), patch(
                "astra_v2.verified_story_history.record_confirmed",
                return_value=True,
            ):
                self.assertEqual(reconcile(youtube, second), ["video-restart-1"])
            self.assertNotIn("video-restart-1", second["pending"])
            self.assertEqual(second["published"]["story-restart-1"]["video_id"],
                             "video-restart-1")
            self.assertEqual(second["confirmed_today"], 1)
            write_json(path, second)

            # A further restart must not count or upload the same video again.
            third = state_for_day(read_json(path))
            self.assertEqual(reconcile(youtube, third), [])
            self.assertEqual(third["confirmed_today"], 1)
            self.assertEqual(len(third["published"]), 1)
            self.assertEqual(third["pending"], {})
            legacy.record_video.assert_called_once()


if __name__ == "__main__":
    unittest.main()
