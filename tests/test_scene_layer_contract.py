"""Regression guards for competing on-screen animations and text safe zones."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.layer_contract import (
    SAFE_REGIONS, overlap_area, scene_layers, verify_scene_layout,
)
from astra_v2.original_stories import catalog


class ExclusivityTests(unittest.TestCase):
    def test_every_original_story_shot_has_one_subject(self):
        shots = [s for story in catalog() for s in story["story_beats"]]
        result = verify_scene_layout(shots)
        self.assertTrue(result["pass"], result["failures"])
        self.assertTrue(result["scenes"])
        self.assertTrue(all(row["competing_foreground_count"] == 1 for row in result["scenes"]))
        self.assertTrue(all(row["foreground"] == "illustration" for row in result["scenes"]))

    def test_robot_and_ship_never_have_extra_animated_cards(self):
        for visual in ("planet", "robot", "ship", "signal", "door", "forest"):
            with self.subTest(visual=visual):
                s = {
                    "visual": visual,
                    "director_asset": "mechanism-diagram",
                    "director_style": "vector-motion",
                    "director_motion": "pulse",
                    "director_layout": "split",
                }
                layers = scene_layers(s)
                self.assertTrue(layers["draw_visual"])
                self.assertFalse(layers["draw_director_asset"])
                self.assertFalse(layers["draw_cached_media"])
                for name in ("composition_overlay", "visual_style_overlay",
                             "attention_overlay", "director_motion_overlay"):
                    self.assertFalse(layers[name], name)

    def test_editorial_asset_also_has_single_foreground(self):
        layers = scene_layers({"visual": "artwork", "director_asset": "source-document"})
        self.assertFalse(layers["draw_visual"])
        self.assertTrue(layers["draw_director_asset"])

    def test_cached_visual_replaces_instead_of_stacking_on_illustration(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "safe.png"
            f.write_bytes(b"placeholder-exists")
            media = {"status": "ready", "cache_image": str(f)}
            chosen = scene_layers({"visual": "media", "resolved_asset": media,
                                   "director_asset": "source-document"})
            self.assertEqual(chosen["foreground"], "cached_media")
            self.assertFalse(chosen["draw_director_asset"])
            self.assertFalse(chosen["draw_visual"])
            # A handcrafted protagonist wins even if a generic asset exists.
            illustrated = scene_layers({"visual": "robot", "resolved_asset": media,
                                        "director_asset": "source-document"})
            self.assertEqual(illustrated["foreground"], "illustration")
            self.assertFalse(illustrated["draw_cached_media"])

    def test_missing_media_fails_closed(self):
        self.assertFalse(verify_scene_layout([{"visual": "media"}])["pass"])
        self.assertIn("missing_media", scene_layers({"visual": "media"})["foreground"])

    def test_title_art_caption_reserved_regions_do_not_overlap(self):
        for first in SAFE_REGIONS:
            for second in SAFE_REGIONS:
                if first == second:
                    continue
                self.assertEqual(overlap_area(SAFE_REGIONS[first], SAFE_REGIONS[second]), 0)
        self.assertTrue(verify_scene_layout([{"visual": "robot"}])["pass"])

    def test_adversarial_geometry_overlap_is_rejected(self):
        invalid = {**SAFE_REGIONS, "caption": (100, 1200, 900, 1600)}
        with patch.dict("astra_v2.layer_contract.SAFE_REGIONS", invalid, clear=True):
            out = verify_scene_layout([{"visual": "robot"}])
        self.assertFalse(out["pass"])
        self.assertTrue(any("unsafe_region_overlap" in x for x in out["failures"]))


if __name__ == "__main__":
    unittest.main()
