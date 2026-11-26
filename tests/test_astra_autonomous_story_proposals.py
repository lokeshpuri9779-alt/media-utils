import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from astra_v2.autonomous_story_proposals import (replenish, proposal, MYSTERIES, MYSTERY_CAUSES, CAUSAL_PATHS, RESOLUTIONS)
from astra_v2.publication_quality import publication_rejection


class AutonomousStoryProposalTests(unittest.TestCase):
    def test_persistent_novelty_and_nonpublication(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "proposals.json"
            first = replenish(path, count=8)
            before = json.loads(path.read_text())
            second = replenish(path, count=8)
            after = json.loads(path.read_text())
            self.assertGreater(first, 0)
            self.assertGreaterEqual(second, 0)
            self.assertEqual(len(after["proposals"]), first + second)
            self.assertEqual(len({s["plot_fingerprint"] for s in after["proposals"]}), first + second)
            self.assertGreater(after["next_index"], before["next_index"])
            self.assertTrue(all(publication_rejection(s) for s in after["proposals"]))

    def test_semantic_duplicates_are_skipped_before_persistence(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "proposals.json"
            from astra_v2.semantic_candidate_index import SemanticCandidateIndex
            original = SemanticCandidateIndex.match
            calls = {"count": 0}

            def reject_first(index, candidate, threshold=0.72):
                calls["count"] += 1
                if calls["count"] == 1:
                    return {"matched_content_id": "prior"}
                return original(index, candidate, threshold)

            with patch.object(SemanticCandidateIndex, "match", reject_first):
                count = replenish(path, count=2)
            state = json.loads(path.read_text())
            self.assertEqual(count, 2)
            self.assertEqual(state["supply_health"]["semantic_duplicates_rejected"], 1)
            self.assertGreater(state["supply_health"]["attempted"], count)
            self.assertTrue(all(not item["production_ready"] for item in state["proposals"]))

    def test_compositional_dimensions_produce_distinct_story_fingerprints(self):
        candidates = [proposal(index) for index in range(300)]
        self.assertEqual(len({item["plot_fingerprint"] for item in candidates}), 300)
        self.assertGreaterEqual(len({item["story_beats"][0]["visual"] for item in candidates}), 8)
        self.assertGreaterEqual(len({item["story_beats"][2]["speech"] for item in candidates}), 8)
        self.assertTrue(all(item["kind"] == "unreviewed_causal_draft" for item in candidates))
        self.assertTrue(all(item["production_ready"] is False for item in candidates))
        self.assertTrue(all(item["title"] != f"Unreviewed story proposal {i + 1}"
                            for i, item in enumerate(candidates)))
        self.assertTrue(all(item["title"].startswith("The ") and "Mystery of the" in item["title"]
                            for item in candidates))

    def test_added_plot_axes_expand_story_supply_variation(self):
        candidates = [proposal(index) for index in range(1200)]
        investigation = {item["story_beats"][1]["speech"] for item in candidates}
        payoff = {item["story_beats"][3]["speech"] for item in candidates}
        self.assertGreaterEqual(len(investigation), 30)
        self.assertGreaterEqual(len(payoff), 30)
        self.assertEqual(len({item["plot_fingerprint"] for item in candidates}), 1200)

    def test_each_visual_tag_is_supported_by_its_own_beat(self):
        import re
        from astra_v2.story_subject_taxonomy import SUBJECTS
        candidates = [proposal(index) for index in range(240)]
        subject_patterns = dict(SUBJECTS)
        for story in candidates:
            for beat in story["story_beats"]:
                tag = beat["visual"]
                if tag == "story":
                    continue
                pattern = subject_patterns.get(tag, r"(?<!\w)" + re.escape(tag) + r"(?!\w)")
                self.assertRegex(beat["speech"], re.compile(pattern, re.I),
                                 msg=f"unsupported visual tag {tag!r}: {beat['speech']}")

    def test_pressure_arcs_stay_inside_the_opening_mystery(self):
        candidates = [proposal(index) for index in range(240)]
        speeches = [" ".join(beat["speech"] for beat in item["story_beats"]).casefold()
                    for item in candidates]
        self.assertGreaterEqual(len(set(speeches)), 240)
        # These were formerly injected by an independent plot-engine axis.
        for unrelated in ("school science fair", "competition prize",
                          "rival rescue teams", "missing delivery"):
            self.assertTrue(all(unrelated not in speech for speech in speeches))
        self.assertTrue(all(any(mystery in item["story_beats"][0]["speech"]
                                for mystery, _, _ in MYSTERIES)
                            for item in candidates))
        self.assertTrue(all("failed" in item["story_beats"][1]["speech"].casefold()
                            for item in candidates))
        self.assertTrue(all(any(cause in item["story_beats"][2]["speech"]
                                    for cause in MYSTERY_CAUSES)
                            for item in candidates))
        self.assertTrue(all(item["production_ready"] is False for item in candidates))

    def test_story_beats_form_a_causal_chain(self):
        item = proposal(37)
        beats = item["story_beats"]
        self.assertEqual([b["story_beat"] for b in beats],
                         ["reveal", "build", "twist", "payoff"])
        self.assertTrue(any(mystery in beats[0]["speech"] for mystery, _, _ in MYSTERIES))
        self.assertTrue(any(test in beats[1]["speech"] for _, test, _, _ in CAUSAL_PATHS))
        self.assertTrue(any(reveal in beats[2]["speech"] for _, _, reveal, _ in CAUSAL_PATHS))
        self.assertTrue(any(resolution in beats[3]["speech"] for resolution in RESOLUTIONS))
        self.assertTrue(all(item["production_ready"] is False for item in [item]))
        self.assertNotIn("..", beats[3]["speech"])

    def test_legacy_generic_titles_are_backfilled_from_story_content(self):
        from astra_v2.autonomous_story_proposals import _backfill_legacy_titles
        items = [{"title": "Unreviewed story proposal 157",
                  "story_beats": [{"visual": "bell",
                                   "speech": "As the keeper in a flooded village, a lighthouse keeper needed to understand why the warning bell rang."}]}]
        self.assertEqual(_backfill_legacy_titles(items), 1)
        self.assertEqual(items[0]["title"], "The Bell Mystery of Flooded Village")

    def test_invalid_indices_and_batch_sizes_rejected(self):
        with self.assertRaises(ValueError):
            proposal(-1)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                replenish(Path(root) / "ledger.json", count=101)


if __name__ == "__main__":
    unittest.main()
