"""Story factory capacity, determinism, and publishing safety."""
import unittest
import tempfile
import json
from pathlib import Path
from astra_v2.story_factory import TARGET, CAPACITY, MECHANISMS, candidate_at, screen_candidate, generate

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
        from astra_v2.story_factory import MECHANISMS
        self.assertEqual(len({candidate_at(i)["premise_key"] for i in range(len(MECHANISMS))}),len(MECHANISMS))
    def test_plot_identity_survives_cosmetic_variations(self):
        from astra_v2.story_factory import MECHANISMS
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
            self.assertEqual(second["last_awaiting_review"],min(31, max(0, len(MECHANISMS)-31)))
            self.assertEqual(sum(json.loads(line)["status"]=="needs_new_plot"
                                 for line in review.read_text().splitlines()), max(0, 62-len(MECHANISMS)))
    def test_expanded_premises_have_distinct_keys(self):
        self.assertGreaterEqual(len(MECHANISMS),54)
        self.assertEqual(len({row[0] for row in MECHANISMS}),len(MECHANISMS))
    def test_third_role_is_not_duplicate_story(self):
        a=candidate_at(0)
        b=candidate_at(len(MECHANISMS)*2)
        self.assertEqual(a["premise_key"],b["premise_key"])
        self.assertNotEqual(a["story_beats"],b["story_beats"])
    def test_scheduled_batch_size_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            output=Path(tmp)/"candidates.jsonl"
            self.assertEqual(generate(state,output,batch_size=500),500)
            first=json.loads(state.read_text())
            self.assertEqual(first["next_slot"],500)
            self.assertEqual(len(output.read_text().splitlines()),500)
            self.assertEqual(first["last_awaiting_review"],len(MECHANISMS))
            self.assertEqual(generate(state,output,batch_size=500),500)
            second=json.loads(state.read_text())
            self.assertEqual(second["next_slot"],1000)
            self.assertEqual(second["last_awaiting_review"],0)
            self.assertEqual(len(output.read_text().splitlines()),500)
    def test_new_mechanisms_enter_after_cursor_advanced(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            output=Path(tmp)/"candidates.jsonl"
            old_keys=[row[0] for row in MECHANISMS[:-8]]
            state.write_text(json.dumps({"next_slot": 10000,
                                         "seen_premise_keys": old_keys,
                                         "seen_plot_signatures": []}))
            self.assertEqual(generate(state, output, batch_size=12),12)
            rows=[json.loads(line) for line in output.read_text().splitlines()]
            reviews=[json.loads(line) for line in output.with_name("story_factory_review.jsonl").read_text().splitlines()]
            self.assertEqual({row["premise_key"] for row in rows[:8]},
                             {row[0] for row in MECHANISMS[-8:]})
            self.assertTrue(all(r["status"]=="awaiting_editorial_review" for r in reviews[:8]))
            self.assertEqual(json.loads(state.read_text())["next_slot"],10012)
            self.assertEqual(len({r["candidate_id"] for r in rows}),12)

    def test_sample_unique_ids(self):
        self.assertEqual(len({candidate_at(i)["candidate_id"] for i in range(1000)}),1000)
if __name__=="__main__": unittest.main()
