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
    def test_causal_annotations_survive_cosmetic_variants(self):
        from astra_v2.causal_premise_review import causal_premise_match
        first = candidate_at(0)
        variant = candidate_at(len(MECHANISMS))
        for field in ("central_conflict", "decisive_choice", "resolution"):
            self.assertTrue(first[field])
            self.assertEqual(first[field], variant[field])
        self.assertIsNotNone(causal_premise_match(variant, [first]))
        self.assertFalse(variant["production_ready"])
        self.assertTrue(variant["editorial_review_required"])

    def test_different_mechanism_is_not_assumed_duplicate(self):
        from astra_v2.causal_premise_review import causal_premise_match
        first = candidate_at(0)
        second = candidate_at(1)
        self.assertIsNone(causal_premise_match(second, [first]))

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
            self.assertEqual(generate(state,output,batch_size=500),len(MECHANISMS))
            first=json.loads(state.read_text())
            self.assertEqual(first["next_slot"],len(MECHANISMS))
            self.assertEqual(len(output.read_text().splitlines()),len(MECHANISMS))
            self.assertEqual(first["last_awaiting_review"],len(MECHANISMS))
            # Once all authored mechanisms are used, keep only the three
            # review-rejected seeds that the rewrite queue can consume.
            self.assertEqual(generate(state,output,batch_size=500),3)
            second=json.loads(state.read_text())
            self.assertEqual(second["next_slot"],len(MECHANISMS)+3)
            self.assertEqual(second["last_awaiting_review"],0)
            self.assertEqual(len(output.read_text().splitlines()),3)
            reviews=[json.loads(x) for x in output.with_name("story_factory_review.jsonl").read_text().splitlines()]
            self.assertTrue(all(r["status"]=="needs_new_plot" for r in reviews))
    def test_new_mechanisms_enter_after_cursor_advanced(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            output=Path(tmp)/"candidates.jsonl"
            old_keys=[row[0] for row in MECHANISMS[:-8]]
            state.write_text(json.dumps({"next_slot": 10000,
                                         "seen_premise_keys": old_keys,
                                         "seen_plot_signatures": []}))
            self.assertEqual(generate(state, output, batch_size=12),8)
            rows=[json.loads(line) for line in output.read_text().splitlines()]
            reviews=[json.loads(line) for line in output.with_name("story_factory_review.jsonl").read_text().splitlines()]
            self.assertEqual({row["premise_key"] for row in rows[:8]},
                             {row[0] for row in MECHANISMS[-8:]})
            self.assertTrue(all(r["status"]=="awaiting_editorial_review" for r in reviews[:8]))
            self.assertEqual(json.loads(state.read_text())["next_slot"],10008)
            self.assertEqual(len({r["candidate_id"] for r in rows}),8)

    def test_fresh_authored_mechanisms_are_distinct_and_review_only(self):
        from astra_v2.story_factory_fresh_premises import FRESH_MECHANISMS
        self.assertEqual(len(FRESH_MECHANISMS),40)
        self.assertEqual(len({m[0] for m in MECHANISMS}),len(MECHANISMS))
        self.assertTrue(all(len(m)==6 and all(isinstance(x,str) and len(x)>7 for x in m)
                            for m in FRESH_MECHANISMS))
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            output=Path(tmp)/"candidates.jsonl"
            # Production state has used every older premise: a fresh source
            # extension must still be discovered at an advanced cursor.
            prior=[m[0] for m in MECHANISMS[:-len(FRESH_MECHANISMS)]]
            state.write_text(json.dumps({"next_slot":43500, "seen_premise_keys":prior}))
            self.assertEqual(generate(state,output,batch_size=500),len(FRESH_MECHANISMS))
            rows=[json.loads(x) for x in output.read_text().splitlines()]
            reviews=[json.loads(x) for x in output.with_name("story_factory_review.jsonl").read_text().splitlines()]
            self.assertEqual({r["premise_key"] for r in rows},
                             {m[0] for m in FRESH_MECHANISMS})
            self.assertTrue(all(r["status"]=="awaiting_editorial_review" and not r["production_ready"]
                                for r in reviews))
            self.assertEqual(json.loads(state.read_text())["next_slot"],43500+len(FRESH_MECHANISMS))

    def test_new_eight_premises_reopen_review_queue_without_publication(self):
        from astra_v2.story_factory_fresh_premises import FRESH_MECHANISMS
        expected = {
            "observatory-heat-haze", "race-rfid-banner",
            "market-bag-score", "library-return-flap",
            "garden-robot-nozzle", "festival-ribbon-static",
            "stage-speaker-vibration", "rain-gauge-roof-splash",
        }
        self.assertEqual({row[0] for row in FRESH_MECHANISMS[-8:]}, expected)
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            output = Path(tmp) / "candidates.jsonl"
            # Reproduce an exhausted persistent state from before these seeds.
            state.write_text(json.dumps({
                "next_slot": 43500,
                "seen_premise_keys": [m[0] for m in MECHANISMS[:-8]],
            }))
            self.assertEqual(generate(state, output, batch_size=500), 8)
            candidates = [json.loads(row) for row in output.read_text().splitlines()]
            reviews = [json.loads(row) for row in output.with_name(
                "story_factory_review.jsonl").read_text().splitlines()]
            self.assertEqual({row["premise_key"] for row in candidates}, expected)
            self.assertTrue(all(row["production_ready"] is False
                                and row["editorial_review_required"] is True
                                and row["independent_plot_claim"] is False
                                for row in candidates))
            self.assertTrue(all(row["status"] == "awaiting_editorial_review"
                                and row["production_ready"] is False
                                for row in reviews))
            # Once the eight are seen, no cosmetic variants are approved.
            self.assertEqual(generate(state, output, batch_size=500), 3)
            rejected = [json.loads(row) for row in output.with_name(
                "story_factory_review.jsonl").read_text().splitlines()]
            self.assertTrue(all(row["status"] == "needs_new_plot"
                                for row in rejected))

    def test_exhausted_premises_do_not_flood_repeated_500_story_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            output=Path(tmp)/"candidates.jsonl"
            state.write_text(json.dumps({"next_slot":43500,
                                         "seen_premise_keys":[m[0] for m in MECHANISMS]}))
            self.assertEqual(generate(state,output,batch_size=500),3)
            reviews=[json.loads(x) for x in output.with_name("story_factory_review.jsonl").read_text().splitlines()]
            self.assertTrue(all(r["issues"]==["repeated_underlying_plot_mechanism"]
                                and not r["production_ready"] for r in reviews))
            self.assertEqual(json.loads(state.read_text())["last_batch"],3)

    def test_sample_unique_ids(self):
        self.assertEqual(len({candidate_at(i)["candidate_id"] for i in range(1000)}),1000)
if __name__=="__main__": unittest.main()
