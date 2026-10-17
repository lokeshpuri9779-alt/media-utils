"""Story factory capacity, determinism, and publishing safety."""
import unittest
import tempfile
import json
from pathlib import Path
from astra_v2.story_factory import TARGET, CAPACITY, candidate_at, screen_candidate, generate

class StoryFactoryTests(unittest.TestCase):
    def test_capacity(self):
        self.assertGreaterEqual(CAPACITY, TARGET)
    def test_bounds(self):
        with self.assertRaises(IndexError): candidate_at(TARGET)
    def test_deterministic_and_unapproved(self):
        for i in (0,1,3000,195999):
            row=candidate_at(i)
            self.assertEqual(row,candidate_at(i))
            self.assertFalse(row["production_ready"])
            self.assertEqual(row["kind"],"unreviewed_causal_draft")
            self.assertEqual(len(row["story_beats"]),4)
    def test_repeated_premise_is_not_approved(self):
        item = candidate_at(0)
        self.assertEqual(screen_candidate(item, [])["status"], "awaiting_editorial_review")
        self.assertEqual(screen_candidate(item, [item["premise_key"]])["status"], "needs_new_plot")
        self.assertFalse(screen_candidate(item, [])["production_ready"])
    def test_first_batch_rotates_premises(self):
        from astra_v2.story_expansion_2000 import MECHANISMS
        self.assertEqual(len({candidate_at(i)["premise_key"] for i in range(len(MECHANISMS))}),len(MECHANISMS))
    def test_plot_identity_survives_cosmetic_variations(self):
        from astra_v2.story_expansion_2000 import MECHANISMS
        first=candidate_at(0)
        second=candidate_at(len(MECHANISMS))
        self.assertNotEqual(first["candidate_id"],second["candidate_id"])
        self.assertEqual(first["plot_signature"],second["plot_signature"])
    def test_end_to_end_resume_and_review_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            output=Path(tmp)/"candidates.jsonl"
            self.assertEqual(generate(state, output, batch_size=31),31)
            first=json.loads(state.read_text())
            self.assertEqual(first["next_slot"],31)
            self.assertEqual(first["last_awaiting_review"],len(first["seen_premise_keys"]))
            review=output.with_name("story_factory_review.jsonl")
            decisions=[json.loads(line) for line in review.read_text().splitlines()]
            self.assertEqual(len(decisions),31)
            self.assertTrue(all(not item["production_ready"] for item in decisions))
            self.assertEqual(generate(state, output, batch_size=31),31)
            second=json.loads(state.read_text())
            self.assertEqual(second["next_slot"],62)
            self.assertEqual(second["last_awaiting_review"],0)
            self.assertTrue(all(json.loads(line)["status"]=="needs_new_plot"
                                for line in review.read_text().splitlines()))
    def test_sample_unique_ids(self):
        self.assertEqual(len({candidate_at(i)["candidate_id"] for i in range(1000)}),1000)
if __name__=="__main__": unittest.main()
