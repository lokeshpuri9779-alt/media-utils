"""Static guardrails for ASTRA's zero-cost GitHub production workflows.

These tests use only the Python standard library and run without API secrets.
They intentionally do not claim end-to-end render or upload success.
"""
from __future__ import annotations

import re
import unittest
from datetime import datetime, timedelta, timezone

from tools.astra_asset_pack_watch import inspect_artifacts, pinned_run_id
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / ".github/workflows/astra-v2-publish.yml"
PRELOAD = ROOT / ".github/workflows/astra-v2-preload.yml"
LONGFORM = ROOT / ".github/workflows/astra-v2-longform.yml"
REQUIREMENTS = ROOT / "requirements.txt"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def visual_pack_run_id(source: str) -> str:
    match = re.search(r"(?m)^\s+run-id:\s*(\d+)\s*$", source)
    if not match:
        raise AssertionError("pinned visual-pack artifact run ID missing")
    return match.group(1)


class GithubReadinessTests(unittest.TestCase):
    def test_diagnostic_import_dependencies_precede_publisher_early_tests(self):
        publisher = read(PUBLISH)
        installer = publisher.index("- name: Install lightweight publisher diagnostic dependencies")
        tests = publisher.index("- name: Test queue and OAuth diagnostics")
        preflight = publisher.index("- name: Reconcile pending uploads and check schedule")
        self.assertLess(installer, tests)
        self.assertLess(tests, preflight)
        self.assertIn("ASTRA_EARLY_IMPORTS=ready", publisher)
        requirements = read(REQUIREMENTS)
        for pinned in ("httpx==0.28.1", "Pillow==11.3.0",
                       "numpy==2.2.6", "imageio-ffmpeg==0.6.0"):
            self.assertIn(pinned, requirements)
            self.assertIn(pinned, publisher)

    def test_four_lane_schedule_is_bounded(self):
        preload = read(PRELOAD)
        self.assertIn("- cron: '*/30 * * * *'", preload)
        self.assertNotIn("- cron: '*/5 * * * *'", preload)
        self.assertIn("lane: [0, 1, 2, 3]", preload)
        self.assertIn("cancel-in-progress: false", preload)

    def test_all_production_paths_pin_the_same_artwork_pack(self):
        publisher, preload, longform = map(read, (PUBLISH, PRELOAD, LONGFORM))
        self.assertEqual(len({visual_pack_run_id(s) for s in
                              (publisher, preload, longform)}), 1)
        for source in (publisher, preload, longform):
            self.assertIn("--expected 3200", source)
            self.assertIn("astra-original-visual-pack", source)
        self.assertIn("ASTRA_ASSET_PACK_ENABLED: ${{ vars.ASTRA_ASSET_PACK_ENABLED || '1' }}", preload)
        self.assertIn("ASTRA_ASSET_PACK_ENABLED: '1'", publisher)

    def test_image_validation_import_precedes_artifact_restoration(self):
        # Both media preload lanes download and validate the pinned pack
        # before their full renderer dependencies, so Pillow is not optional.
        for workflow in (PRELOAD, LONGFORM):
            with self.subTest(workflow=workflow.name):
                source = read(workflow)
                minimal = source.index("- name: Install pinned asset validation dependency")
                download = source.index("- name: Download reviewed reusable visual pack")
                restore = source.index("- name: Verify restored reusable visual pack")
                full = source.index("- name: Install rendering stack") if workflow == PRELOAD else source.index("- name: Install free rendering dependencies")
                self.assertLess(minimal, download)
                self.assertLess(download, restore)
                self.assertLess(restore, full)
                self.assertIn("Pillow==11.3.0", source)
                self.assertIn("ASTRA_ASSET_VALIDATION_IMPORT=ready", source)

    def test_preload_probe_must_decode_real_mp4(self):
        preload = read(PRELOAD)
        self.assertIn("ASTRA_FFPROBE_EXTRACTED_RUNTIME_UNAVAILABLE=1", preload)
        self.assertIn("ASTRA_FFPROBE_REAL_MP4_SMOKE=passed", preload)
        self.assertIn("ffprobe -version >/dev/null 2>&1", preload)
        self.assertIn("apt-get install -y --no-install-recommends ffmpeg", preload)
        self.assertIn("color=c=black:s=160x288:r=2", preload)
        self.assertIn('"codec_type") == "video"', preload)
        self.assertLess(preload.index("ASTRA_FFPROBE_REAL_MP4_SMOKE=passed"),
                        preload.index("- name: Refresh free licensed visual icon cache"))

    def test_visual_pack_expiry_and_missing_artifacts_fail_closed(self):
        now = datetime(2026, 10, 25, tzinfo=timezone.utc)
        def item(days):
            return {"artifacts": [{"name": "astra-original-visual-pack",
                                   "id": 123, "size_in_bytes": 1024,
                                   "expired": False,
                                   "expires_at": (now + timedelta(days=days)).isoformat()}]}
        self.assertEqual(inspect_artifacts(item(15), now=now)["status"], "ok")
        self.assertEqual(inspect_artifacts(item(5), now=now)["status"], "renewal_required")
        self.assertEqual(inspect_artifacts(item(-1), now=now)["status"], "expired")
        self.assertEqual(inspect_artifacts({"artifacts": []}, now=now)["status"], "missing_or_duplicate")
        self.assertGreater(pinned_run_id(ROOT), 0)

    def test_longform_stays_isolated_until_publishing_proof(self):
        publisher, longform = read(PUBLISH), read(LONGFORM)
        self.assertIn("ASTRA_LONG_ENABLED: '0'", publisher)
        self.assertIn("ASTRA_LONG_ONLY: '1'", longform)
        self.assertIn("ASTRA_OPENAI_ALLOW_PAID_API: '0'", publisher)
        self.assertIn("ASTRA_OPENAI_ALLOW_PAID_API: '0'", longform)


if __name__ == "__main__":
    unittest.main()
