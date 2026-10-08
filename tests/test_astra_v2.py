"""Offline safety tests; run before every ASTRA V2 publishing job."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from astra_v2.control import due, quota_resume, state_for_day, write_json, read_json
from astra_v2.creative import CreativeSkip, inspect_video
from astra_v2.run import reconcile
from astra_v2.youtube import Youtube, YoutubeError, reason_for


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, 13, 0, tzinfo=timezone.utc)

    def test_daily_reset_keeps_deduplication(self):
        state = state_for_day(None, self.now)
        state["attempts"] = 48
        state["published"]["story-1"] = {"video_id": "abc"}
        future = state_for_day(state, self.now + timedelta(days=1))
        self.assertEqual(future["attempts"], 0)
        self.assertIn("story-1", future["published"])

    def test_daily_cap(self):
        state = state_for_day(None, self.now)
        state["attempts"] = 48
        self.assertEqual(due(state, self.now)[1], "daily_cap")

    def test_interval(self):
        state = state_for_day(None, self.now)
        state["last_attempt_at"] = self.now.isoformat()
        self.assertEqual(due(state, self.now + timedelta(minutes=10))[1], "min_interval")
        self.assertTrue(due(state, self.now + timedelta(minutes=26))[0])

    def test_quota_backoff(self):
        state = state_for_day(None, self.now)
        resume = quota_resume(self.now, "uploadLimitExceeded")
        self.assertGreaterEqual(resume, self.now + timedelta(hours=24))
        state["blocked_until"] = resume.isoformat()
        self.assertEqual(due(state, self.now)[1], "quota_cooldown")

    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            write_json(target, {"version": 2})
            self.assertEqual(read_json(target)["version"], 2)


class YoutubeTests(unittest.TestCase):
    def test_quota_reason(self):
        response = Mock()
        response.json.return_value = {"error": {"errors": [{"reason": "uploadLimitExceeded"}]}}
        self.assertEqual(reason_for(response), "uploadLimitExceeded")

    def test_wrong_authorized_channel_blocks_upload(self):
        youtube = Youtube("UC_expected_123456789")
        try:
            with patch.dict("os.environ", {
                "YOUTUBE_CLIENT_ID": "id", "YOUTUBE_CLIENT_SECRET": "secret",
                "YOUTUBE_REFRESH_TOKEN": "refresh",
            }):
                token_response = Mock(status_code=200)
                token_response.json.return_value = {"access_token": "temporary"}
                youtube.client.post = Mock(return_value=token_response)
                youtube.get = Mock(return_value={"items": [{"id": "UC_other_123456789"}]})
                with self.assertRaisesRegex(RuntimeError, "different channel"):
                    youtube.authorize()
        finally:
            youtube.client.close()

    def test_pending_processing_not_a_confirmed_success(self):
        state = state_for_day()
        state["pending"]["vid123"] = {"content_id": "story-123", "day": state["day"]}
        youtube = Mock()
        youtube.status.return_value = {"privacyStatus": "public", "uploadStatus": "uploaded"}
        self.assertEqual(reconcile(youtube, state), [])
        self.assertEqual(state["confirmed_today"], 0)
        youtube.status.return_value = {"privacyStatus": "public", "uploadStatus": "processed"}
        # Reconciliation can be tested without importing the heavy Studio runtime.
        with patch.dict("sys.modules", {"cloud_once": SimpleNamespace(CONTENT_META={},
                             record_video=lambda video_id, title: None)}):
            self.assertEqual(reconcile(youtube, state), ["vid123"])
        self.assertEqual(state["confirmed_today"], 1)
        self.assertIn("story-123", state["published"])

    def test_private_video_never_counted(self):
        state = state_for_day()
        state["pending"]["vid123"] = {"content_id": "story-123", "day": state["day"]}
        youtube = Mock()
        youtube.status.return_value = {"privacyStatus": "private", "uploadStatus": "processed"}
        self.assertFalse(reconcile(youtube, state))
        self.assertFalse(state["published"])
        self.assertIn("vid123", state["needs_review"])


class QualityTests(unittest.TestCase):
    def test_requires_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "short.mp4"
            video.write_bytes(b"0" * 35000)
            result = Mock(returncode=0, stdout=json.dumps({
                "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
                "format": {"duration": "28"},
            }))
            with patch("astra_v2.creative.subprocess.run", return_value=result):
                with self.assertRaises(CreativeSkip):
                    inspect_video(video)

    def test_longform_landscape_audio_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "long.mp4"
            video.write_bytes(b"0" * 35000)
            result = Mock(returncode=0, stdout=json.dumps({
                "streams": [{"codec_type": "video", "width": 1920, "height": 1080},
                            {"codec_type": "audio"}],
                "format": {"duration": "240"},
            }))
            with patch("astra_v2.creative.subprocess.run", return_value=result):
                self.assertEqual(inspect_video(video, fmt="long")["seconds"], 240.0)
            with patch("astra_v2.creative.subprocess.run", return_value=result):
                with self.assertRaises(CreativeSkip):
                    inspect_video(video, fmt="short")


if __name__ == "__main__":
    unittest.main()
