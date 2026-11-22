"""Review-only shot/continuity packets for ASTRA's fourth parallel lane."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import astra_offline_storyboard as board


class OfflineStoryboardTests(unittest.TestCase):
    def test_all_reference_stories_produce_twelve_review_only_shots(self):
        result = board.build_packet()
        self.assertEqual(result["experiment"], "astra-offline-storyboards-v1")
        self.assertEqual(result["reference_count"], 3)
        self.assertEqual(result["total_shots"], 12)
        self.assertEqual(len(result["packets"]), 3)
        self.assertFalse(result["frames_rendered"])
        self.assertFalse(result["real_model_inference_executed"])
        self.assertEqual(result["semantic_fidelity"], "not_verified")
        self.assertTrue(result["manual_editorial_and_visual_review_required"])
        for label in ("approved", "production_ready", "published",
                      "replaces_astra_main"):
            self.assertFalse(result[label])
        for packet in result["packets"]:
            self.assertTrue(packet["event_state_contract_valid"])
            self.assertEqual(len(packet["shots"]), 4)
            self.assertEqual(len(packet["story_digest"]), 64)
            self.assertEqual([s["stage"] for s in packet["shots"]],
                             list(board.STAGES))
            self.assertEqual(
                len({s["character_anchor"] for s in packet["shots"]}), 1
            )
            self.assertEqual(
                len({s["location_anchor"] for s in packet["shots"]}), 1
            )
            self.assertEqual(packet["shot_count"], 4)
            self.assertFalse(packet["production_ready"])
            for prev, current in zip(packet["shots"], packet["shots"][1:]):
                self.assertEqual(prev["after_state"], current["before_state"])
            for shot in packet["shots"]:
                self.assertIn(shot["focus_state"], shot["after_state"])
                self.assertTrue(set(shot["props"]) <= set(packet["assets"]))
                self.assertIn(shot["shot_type"], board.SHOT_TYPES)
                self.assertFalse(shot["frame_generation_executed"])
                self.assertTrue(shot["manual_visual_review_required"])
                self.assertEqual(shot["asset_verification"], "not_verified")

    def test_unknown_asset_or_focus_state_fails_closed(self):
        broken = deepcopy(board.BLUEPRINTS)
        broken["glasshouse-sunshade"]["shots"][0]["props"].append(
            "made_up_prop")
        with self.assertRaisesRegex(ValueError, "undeclared"):
            board.build_packet(blueprints=broken)
        broken = deepcopy(board.BLUEPRINTS)
        broken["glasshouse-sunshade"]["shots"][1]["focus_state"] = "no_such_state"
        with self.assertRaisesRegex(ValueError, "not actually created"):
            board.build_packet(blueprints=broken)

    def test_reordered_shots_fail_closed(self):
        broken = deepcopy(board.BLUEPRINTS)
        shots = broken["footbridge-ducklings"]["shots"]
        shots[1], shots[2] = shots[2], shots[1]
        with self.assertRaisesRegex(ValueError, "stage order"):
            board.build_packet(blueprints=broken)

    def test_undeclared_case_or_duplicate_reference_fails(self):
        broken = deepcopy(board.BLUEPRINTS)
        broken["unknown-story"] = deepcopy(broken["glasshouse-sunshade"])
        with self.assertRaisesRegex(ValueError, "match reference cases"):
            board.build_packet(blueprints=broken)
        from tools.astra_offline_reference_benchmark import REFERENCE_CASES
        duplicated = deepcopy(REFERENCE_CASES)
        duplicated[1] = deepcopy(duplicated[0])
        with self.assertRaisesRegex(ValueError, "duplicate case"):
            board.build_packet(cases=duplicated)

    def test_impossible_scene_ledger_fails_before_shot_packet(self):
        from tools.astra_offline_reference_benchmark import REFERENCE_CASES
        broken = deepcopy(REFERENCE_CASES)
        broken[2]["scenes"][1]["requires"].append("never_had_this_state")
        with self.assertRaisesRegex(ValueError, "unmet preconditions"):
            board.build_packet(cases=broken)

    def test_visual_specs_are_bounded_and_not_blank(self):
        broken = deepcopy(board.BLUEPRINTS)
        broken["moon-mirror-garden"]["shots"][0]["motion"] = "still"
        with self.assertRaisesRegex(ValueError, "missing or unbounded"):
            board.build_packet(blueprints=broken)
        broken = deepcopy(board.BLUEPRINTS)
        broken["moon-mirror-garden"]["shots"][0]["props"] = []
        with self.assertRaisesRegex(ValueError, "undeclared or duplicate"):
            board.build_packet(blueprints=broken)

    def test_packet_is_deterministic_and_still_unapproved_when_exported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "shots.json"
            with patch("sys.argv", ["storyboard", "--output", str(p)]):
                board.main()
            first = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(first, board.build_packet())
            self.assertFalse(first["approved"])
            self.assertFalse(first["frames_rendered"])


if __name__ == "__main__":
    unittest.main()
