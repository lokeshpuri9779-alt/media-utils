"""Conservative scheduled Shorts saturation guard, no GitHub/YouTube writes."""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from astra_v2.preload_saturation import scheduled_shorts_skip
from astra_v2 import preload_queue


BASE = {
    "GITHUB_EVENT_NAME": "schedule",
    "ASTRA_PRELOAD_LANE": "2",
    "ASTRA_PRELOAD_LANES": "4",
    "ASTRA_PRELOAD_BUFFER": "24",
    "ASTRA_LONG_ENABLED": "0",
    "ASTRA_SERIALIZED_PRELOAD": "0",
}
FULL = {"preflight_eligible": 24, "run_lookup_failed": 0}
PROOF = {"checked": 4, "policy_passed": 4, "integrity_failed": 0,
         "download_failed": 0}


class SaturationPolicyTests(unittest.TestCase):
    def decide(self, env=BASE, inventory=None, sample=None):
        inv = lambda *a, **k: FULL if inventory is None else inventory
        integrity = lambda *a, **k: PROOF if sample is None else sample
        return scheduled_shorts_skip(excluded_ids={"published-x"},
                                    env=env, inventory=inv, sample=integrity)

    def test_skip_only_trusted_recent_full_buffer_with_four_policy_approved_samples(self):
        outcome = self.decide()
        self.assertTrue(outcome["skip"])
        self.assertEqual(outcome["sample_checked"], 4)
        self.assertEqual(outcome["reason"], "bounded_verified_buffer_saturated")

    def test_one_canary_lane_always_renders_and_manual_and_push_always_render(self):
        for edits in ({"ASTRA_PRELOAD_LANE": "0"}, {"GITHUB_EVENT_NAME": "push"},
                      {"GITHUB_EVENT_NAME": "workflow_dispatch"},
                      {"ASTRA_LONG_ENABLED": "1"}, {"ASTRA_LONG_ONLY": "1"},
                      {"ASTRA_SERIALIZED_PRELOAD": "1"},
                      {"ASTRA_PRELOAD_FORCE_RENDER": "1"},
                      {"ASTRA_PRELOAD_REVIEWED_ART_MANIFEST": "reviewed.json"}):
            with self.subTest(edits=edits):
                def never(*a, **k):
                    raise AssertionError("Guard performed unnecessary queue I/O")
                outcome = scheduled_shorts_skip(env={**BASE, **edits},
                                                 inventory=never, sample=never)
                self.assertFalse(outcome["skip"])

    def test_incomplete_trust_or_validity_cannot_skip(self):
        for inventory, sample in (
            ({"preflight_eligible": 23}, PROOF),
            ({"preflight_eligible": 24, "run_lookup_failed": 1}, PROOF),
            (FULL, {**PROOF, "checked": 3}),
            (FULL, {**PROOF, "policy_passed": 3}),
            (FULL, {**PROOF, "download_failed": 1}),
            (FULL, {**PROOF, "integrity_failed": 1}),
        ):
            with self.subTest(inventory=inventory, sample=sample):
                self.assertFalse(self.decide(inventory=inventory, sample=sample)["skip"])

    def test_inaccessible_queue_fails_open(self):
        def down(*a, **k):
            raise TimeoutError("offline")
        decision = scheduled_shorts_skip(env=BASE, inventory=down, sample=down)
        self.assertFalse(decision["skip"])
        self.assertIn("TimeoutError", decision["reason"])

    def test_sampled_video_is_still_not_called_publisher_verified(self):
        decision = self.decide()
        self.assertIn("not_publisher_confirmation", decision["evidence"])


class BoundedQueueTests(unittest.TestCase):
    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    def test_inventory_trust_lookups_stop_at_required_depth(self):
        entries = [
            {"id": i + 1, "name": "astra-preloaded-" + str(i), "expired": False,
             "created_at": "2026-10-25T15:00:00Z",
             "workflow_run": {"id": 99, "head_branch": "main"}}
            for i in range(100)
        ]
        from datetime import datetime, timezone
        with patch.object(preload_queue, "artifacts", return_value=entries), \
             patch.object(preload_queue, "_api", return_value={
                 "conclusion": "success", "head_branch": "main",
                 "name": "ASTRA V2 - Preload Approved Videos",
             }) as api:
            report = preload_queue.inventory_eligibility_snapshot(
                max_age_hours=4, now=datetime(2026, 10, 25, 16, tzinfo=timezone.utc),
                min_required=24)
        self.assertEqual(report["preflight_eligible"], 24)
        api.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    def test_hash_valid_artifact_must_also_pass_current_policy(self):
        cid = "original-eligible"
        video = b"fake-video-chunk" * 100
        artifact = io.BytesIO()
        with zipfile.ZipFile(artifact, "w") as z:
            z.writestr("candidate.json", json.dumps({
                "content_id": cid, "genre": "fiction", "format": "short",
                "renderer": "studio-7.3.1",
                "sha256": hashlib.sha256(video).hexdigest(),
            }))
            z.writestr("video.mp4", video)
        entry = {"id": 27, "name": "astra-preloaded-" + cid,
                 "created_at": "2026-10-25T15:00:00Z",
                 "workflow_run": {"id": 90}}
        def fake_download(args, **kwargs):
            kwargs["stdout"].write(artifact.getvalue())
            return SimpleNamespace(returncode=0)
        from datetime import datetime, timezone
        with patch.object(preload_queue, "artifacts", return_value=[entry]), \
             patch.object(preload_queue, "_api", return_value={
                 "conclusion": "success", "head_branch": "main",
                 "name": "ASTRA V2 - Preload Approved Videos",
             }), \
             patch.object(preload_queue.subprocess, "run", side_effect=fake_download), \
             patch("astra_v2.publication_quality.publication_rejection", return_value="renderer_incompatible") as gate:
            proof = preload_queue.package_integrity_snapshot(
                max_packages=1, max_age_hours=0, format_filter="short",
                verify_publication_policy=True,
                preflight={"preflight_eligible": 1}, download_timeout_seconds=15)
        self.assertEqual(proof["checked"], 1)
        self.assertEqual(proof["integrity_passed"], 1)
        self.assertEqual(proof["policy_passed"], 0)
        self.assertEqual(proof["policy_rejected"], 1)
        gate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
