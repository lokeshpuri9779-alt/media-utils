"""Production supply status must reflect usable post-history candidates."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.story_supply_diagnostic import diagnose


class StorySupplyExhaustionStatusTests(unittest.TestCase):
    def test_prehistory_candidates_do_not_mask_exhaustion(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "publisher.json"
            history = Path(folder) / "history.json"
            state.write_text(json.dumps({"last_production_result": {
                "outcome": "quality_skip", "reason": "no_approved_original_story_available"
            }}), encoding="utf-8")
            history.write_text("[]", encoding="utf-8")
            inventory_result = {
                "eligible_after_history_and_editorial": 0,
                "authored_candidates": 253, "blocked": 253,
                "block_reasons": {"narrative_duplicate": 95},
                "history_records": 693,
            }
            with patch("astra_v2.story_supply_diagnostic.inventory",
                       return_value=inventory_result), patch(
                       "astra_v2.story_supply_diagnostic.forge_catalog",
                       return_value=[{}] * 95), patch(
                       "astra_v2.story_supply_diagnostic.approved_authored_candidates",
                       return_value=[{}] * 95):
                result = diagnose(state, history)
            self.assertEqual(result["status"], "supply_exhausted")
            self.assertEqual(result["approved_production_candidates_before_history"], 95)
            self.assertEqual(result["eligible"], 0)
            self.assertEqual(result["latest_production_outcome"], "quality_skip")
            self.assertTrue(result["read_only"])
            self.assertEqual(json.loads(history.read_text()), [])

    def test_available_posthistory_candidates_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "publisher.json"
            history = Path(folder) / "history.json"
            state.write_text("{}", encoding="utf-8")
            history.write_text("[]", encoding="utf-8")
            with patch("astra_v2.story_supply_diagnostic.inventory",
                       return_value={
                           "eligible_after_history_and_editorial": 2,
                           "authored_candidates": 253, "blocked": 251,
                           "block_reasons": {}, "history_records": 10,
                       }), patch("astra_v2.story_supply_diagnostic.forge_catalog",
                                 return_value=[]), patch(
                       "astra_v2.story_supply_diagnostic.approved_authored_candidates",
                       return_value=[]):
                result = diagnose(state, history)
            self.assertEqual(result["status"], "approved_candidates_present")
            self.assertEqual(result["eligible"], 2)
            self.assertEqual(result["approved_production_candidates_before_history"], 0)

    def test_missing_history_never_reports_supply_available(self):
        with tempfile.TemporaryDirectory() as folder:
            result = diagnose(Path(folder) / "missing.json",
                              Path(folder) / "history.json")
            self.assertEqual(result["status"], "history_unavailable")
            self.assertTrue(result["read_only"])


if __name__ == "__main__":
    unittest.main()
