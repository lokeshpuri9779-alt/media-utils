"""Regression checks for ASTRA's post-verification immutable artwork cache.

A validated pack must be immutable before decoded frames/inventory are reused.
These tests never render, upload, publish, or approve an artifact.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from astra_v2 import visual_artifact_backdrop as backdrop


ROOT = Path(__file__).resolve().parents[1]


class VerifiedPackCacheTests(unittest.TestCase):
    def test_cached_frame_reuse_is_explicitly_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "art" / "assets").mkdir(parents=True)
            (root / "art" / "manifest.json").write_text('{"assets": []}')
            Image.new("RGB", (60, 90), (35, 75, 110)).save(
                root / "art" / "assets" / "forest.png"
            )
            asset = {"id": "forest", "path": "art/assets/forest.png",
                     "sha256": "verified-upstream"}
            img = Image.new("RGB", (64, 96))
            shot = {"scene_environment": "forest"}
            with patch("astra_v2.quality_asset_selector.select_assets",
                       return_value=[asset]) as selector, \
                 patch("astra_v2.asset_usage_audit.observe"):
                backdrop._cached_pack_background.cache_clear()
                with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ENABLED": "1",
                                             "ASTRA_ASSET_PACK_IMMUTABLE": "1"}):
                    outputs = [
                        backdrop.apply_pack_background(img, shot, "story-1",
                                                       root=root, shot_number=1)
                        for _ in range(3)
                    ]
                    self.assertEqual(selector.call_count, 1)
                    self.assertTrue(all(x.getpixel((0, 0)) == outputs[0].getpixel((0, 0))
                                        for x in outputs))
                selector.reset_mock()
                with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ENABLED": "1"}, clear=True):
                    for _ in range(3):
                        backdrop.apply_pack_background(img, shot, "story-1",
                                                       root=root, shot_number=1)
                    self.assertEqual(selector.call_count, 3)
                backdrop._cached_pack_background.cache_clear()

    def test_both_render_workflows_opt_in_after_validated_restore(self):
        paths = {
            ".github/workflows/astra-v2-preload.yml":
                "Render and approve next original video",
            ".github/workflows/astra-v2-publish.yml":
                "Generate, validate, publish, and verify",
        }
        for path, next_step in paths.items():
            with self.subTest(path=path):
                body = (ROOT / path).read_text(encoding="utf-8")
                restored = body.index(
                    "python -m tools.astra_restore_visual_pack "
                    "runtime-artifacts/download/astra-visual-pack.zip "
                    "runtime-artifacts/verified-pack --expected 3200"
                )
                cache_on = body.index(
                    "echo 'ASTRA_ASSET_PACK_IMMUTABLE=1' >> \"$GITHUB_ENV\""
                )
                rendered = body.index("- name: " + next_step)
                self.assertLess(restored, cache_on)
                self.assertLess(cache_on, rendered)
                self.assertEqual(body.count("echo 'ASTRA_ASSET_PACK_IMMUTABLE=1'"), 1)
                # Never claim the pack is immutable before its hash/count gate.
                self.assertNotIn("ASTRA_ASSET_PACK_IMMUTABLE:", body[:restored])


if __name__ == "__main__":
    unittest.main()
