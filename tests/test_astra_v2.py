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
                with self.assertRaisesRegex(RuntimeError, "channel_mismatch"):
                    youtube.authorize()
        finally:
            youtube.client.close()

    def test_invalid_grant_reason_is_reported_safely(self):
        response = Mock()
        response.json.return_value = {"error": "invalid_grant",
                                      "error_description": "Sensitive server message"}
        self.assertEqual(reason_for(response), "invalid_grant")

    def test_fallback_oauth_preserves_exact_channel_lock(self):
        expected = "UCc9fHSuRnqq_C2C0DpLyRRg"
        youtube = Youtube(expected)
        failed = Mock(status_code=400)
        failed.json.return_value = {"error": "invalid_grant"}
        worked = Mock(status_code=200)
        worked.json.return_value = {"access_token": "temporary-access-token"}
        try:
            with patch.dict("os.environ", {
                "YOUTUBE_CLIENT_ID": "id-primary",
                "YOUTUBE_CLIENT_SECRET": "secret-primary",
                "YOUTUBE_REFRESH_TOKEN": "invalid-refresh",
                "YOUTUBE_COMMUNITY_CLIENT_ID": "id-community",
                "YOUTUBE_COMMUNITY_CLIENT_SECRET": "secret-community",
                "YOUTUBE_COMMUNITY_REFRESH_TOKEN": "valid-refresh",
                "ASTRA_OAUTH_PRIORITY": "primary",
            }, clear=True):
                youtube.client.post = Mock(side_effect=[failed, worked])
                youtube.get = Mock(return_value={
                    "items": [{"id": expected, "contentDetails": {}}]})
                self.assertEqual(youtube.authorize()["id"], expected)
                self.assertEqual(youtube.credential_alias, "community")
                self.assertEqual(youtube.client.post.call_count, 2)
        finally:
            youtube.client.close()

    def test_channel_mismatched_backup_is_refused(self):
        youtube = Youtube("UCc9fHSuRnqq_C2C0DpLyRRg")
        good_refresh = Mock(status_code=200)
        good_refresh.json.return_value = {"access_token": "temporary"}
        try:
            with patch.dict("os.environ", {
                "YOUTUBE_COMMUNITY_CLIENT_ID": "cid",
                "YOUTUBE_COMMUNITY_CLIENT_SECRET": "csecret",
                "YOUTUBE_COMMUNITY_REFRESH_TOKEN": "refresh",
            }, clear=True):
                youtube.client.post = Mock(return_value=good_refresh)
                youtube.get = Mock(return_value={
                    "items": [{"id": "UCwrongchannel123456789"}]})
                with self.assertRaisesRegex(RuntimeError, "channel_mismatch"):
                    youtube.authorize()
                self.assertIsNone(youtube.token)
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



class WatchdogTests(unittest.TestCase):
    def test_watchdog_detects_stale_confirmed_video(self):
        from astra_v2.health import assess
        now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
        state = state_for_day(None, now)
        state["published"]["old"] = {"confirmed_at": (now - timedelta(hours=26)).isoformat()}
        self.assertEqual(assess(state, now)[0], "unhealthy")

    def test_watchdog_respects_initial_grace(self):
        from astra_v2.health import assess
        now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
        state = state_for_day(None, now)
        self.assertEqual(assess(state, now)[0], "healthy")


class PreflightTests(unittest.TestCase):
    def test_public_processed_video_is_confirmed_once_and_fed_back(self):
        import os
        from astra_v2.preflight import reconcile_pending
        with tempfile.TemporaryDirectory() as directory:
            prior = Path.cwd()
            os.chdir(directory)
            try:
                write_json("performance.json", {"videos": {}, "strategy": {"retain": True}})
                state = state_for_day()
                state["pending"]["video123"] = {
                    "content_id": "original-story-one", "title": "The Last Lightkeeper",
                    "format": "short", "genre": "fiction", "day": state["day"],
                }
                youtube = Mock()
                youtube.status.return_value = {
                    "privacyStatus": "public", "uploadStatus": "processed",
                }
                confirmed, pending, review = reconcile_pending(youtube, state, "rayvan")
                self.assertEqual((confirmed, pending, review), (["video123"], [], []))
                self.assertEqual(state["confirmed_today"], 1)
                self.assertIn("original-story-one", state["published"])
                saved = read_json("performance.json")
                self.assertTrue(saved["strategy"]["retain"])
                self.assertEqual(saved["videos"]["video123"]["visibility"], "public")
                self.assertIn("video123", Path("SHORTS.md").read_text())
                self.assertEqual(reconcile_pending(youtube, state, "rayvan")[0], [])
                self.assertEqual(state["confirmed_today"], 1)
            finally:
                os.chdir(prior)

    def test_unfinished_video_stays_pending_and_is_not_reported_as_success(self):
        from astra_v2.preflight import reconcile_pending
        state = state_for_day()
        state["pending"]["video123"] = {"content_id": "story123", "day": state["day"]}
        youtube = Mock()
        youtube.status.return_value = {
            "privacyStatus": "public", "uploadStatus": "uploaded",
        }
        confirmed, pending, review = reconcile_pending(youtube, state, "rayvan")
        self.assertEqual((confirmed, pending, review), ([], ["video123"], []))
        self.assertEqual(state["confirmed_today"], 0)
        self.assertIn("video123", state["pending"])

    def test_private_video_is_never_claimed_public(self):
        from astra_v2.preflight import reconcile_pending
        state = state_for_day()
        state["pending"]["video123"] = {"content_id": "story123", "day": state["day"]}
        youtube = Mock()
        youtube.status.return_value = {
            "privacyStatus": "private", "uploadStatus": "processed",
        }
        confirmed, pending, review = reconcile_pending(youtube, state, "rayvan")
        self.assertEqual((confirmed, pending, review), ([], [], ["video123"]))
        self.assertFalse(state["published"])
        self.assertEqual(state["confirmed_today"], 0)
        self.assertIn("video123", state["needs_review"])

if __name__ == "__main__":
    unittest.main()
