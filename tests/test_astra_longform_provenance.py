"""Long-form Studio renderer identity must survive packaging (no real upload)."""
from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.creative import CreativeSkip, make_long_candidate
from astra_v2.preload_queue import prepare


def fake_module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


class LongformProvenanceTests(unittest.TestCase):
    def _candidate(self, renderer):
        legacy = fake_module(
            "cloud_once",
            CONTENT_META={
                "renderer": renderer, "format": "long", "genre": "current",
                "content_id": "trend-brief-test", "source": "https://example.org/source",
            },
            make_long=lambda path, episode: ("Source-backed long story", "Description"),
            load_performance=lambda: {},
        )
        modules = {
            "cloud_once": legacy,
            "longform": fake_module("longform", choose_episode=lambda *a, **k: "trend-brief-test"),
            "ypp_safety": fake_module("ypp_safety", enforce=lambda *a, **k: {"pass": True}),
            "astra_v2.cover_frames": fake_module("astra_v2.cover_frames", extract_long_cover=lambda *a: None),
        }
        with patch.dict(sys.modules, modules), \
             patch.dict(os.environ, {"ASTRA_LONG_ENABLED": "1"}), \
             patch("astra_v2.creative.inspect_video", return_value={
                 "seconds": 96.55, "width": 1920, "height": 1080, "size": 50000,
             }):
            return make_long_candidate(Path("synthetic-dry-run.mp4"), set(), set())

    def test_verified_long_renderer_is_preserved(self):
        candidate = self._candidate("studio-7.3.1")
        self.assertEqual(candidate["renderer"], "studio-7.3.1")
        self.assertEqual(candidate["format"], "long")
        self.assertEqual(candidate["media"]["width"], 1920)

    def test_unknown_renderer_fails_closed(self):
        for identity in (None, "", "unknown"):
            with self.subTest(identity=identity), self.assertRaisesRegex(
                CreativeSkip, "longform_missing_verified_renderer_provenance"
            ):
                self._candidate(identity)

    def test_package_preserves_real_longform_provenance(self):
        candidate = self._candidate("studio-7.3.1")
        # Isolate JSON packaging from actual video encoding; the real
        # production run separately decodes its MP4 with ffprobe.
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "render.mp4"
            path.write_bytes(b"synthetic-video-bytes")
            with patch("astra_v2.creative.inspect_video", return_value=candidate["media"]):
                package = prepare(path, candidate)
            archived = json.loads((package / "candidate.json").read_text())
            self.assertEqual(archived["renderer"], "studio-7.3.1")
            self.assertEqual(archived["format"], "long")


if __name__ == "__main__":
    unittest.main()
