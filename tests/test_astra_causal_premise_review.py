import re
import unittest
from unittest.mock import patch

from astra_v2.causal_premise_review import CausalPremiseIndex, causal_premise_match
from astra_v2.story_editorial import triage


def story(content_id, conflict="winter grain shortage", choice="share the last grain",
          resolution="both families survive together"):
    return {
        "content_id": content_id,
        "title": content_id,
        "central_conflict": conflict,
        "decisive_choice": choice,
        "resolution": resolution,
        "story_beats": [{"speech": "distinct dialogue " + content_id}],
    }


class CausalPremiseReviewTests(unittest.TestCase):
    def test_reworded_title_and_dialogue_cannot_hide_identical_annotated_arc(self):
        match = causal_premise_match(story("second"), [story("first")])
        self.assertEqual(match["matched_content_id"], "first")
        self.assertTrue(match["review_required"])
        self.assertFalse(match["publication_approved"])

    def test_different_resolution_not_flagged(self):
        self.assertIsNone(causal_premise_match(
            story("second", resolution="grain is lost in the flood"),
            [story("first")]))

    def test_missing_explicit_annotations_never_inferred_from_narration(self):
        self.assertIsNone(causal_premise_match(
            {"story_beats": [{"speech": "share the last grain"}]}, [story("first")]))

    def test_recurring_character_alone_is_not_repeat(self):
        first = story("first")
        first["character_id"] = "mara"
        second = story("second", choice="plant grain for next season")
        second["character_id"] = "mara"
        self.assertIsNone(causal_premise_match(second, [first]))

    def test_triage_exposes_review_evidence_without_approval(self):
        result = triage([story("second")], history=[story("first")])
        item = (result["ready_for_review"] + result["needs_work"])[0]
        self.assertEqual(item["causal_repeat_review"]["matched_content_id"], "first")
        self.assertNotIn("production_ready", item)


    @staticmethod
    def _linear_reference(candidate, history):
        fields = ("central_conflict", "decisive_choice", "resolution")
        def key(value):
            if not isinstance(value, dict):
                return None
            parts = tuple(" ".join(re.findall(r"[a-z0-9]+", str(value.get(field) or "").casefold()))
                          for field in fields)
            return parts if all(parts) else None
        candidate_key = key(candidate)
        if candidate_key is None:
            return None
        for prior in history:
            if key(prior) == candidate_key:
                return {
                    "matched_content_id": prior.get("content_id"),
                    "matched_title": prior.get("title"),
                    "method": "explicit_causal_arc_match",
                    "review_required": True,
                    "publication_approved": False,
                }
        return None

    def test_index_matches_linear_reference_with_missing_and_non_dict_history(self):
        history = [None, "bad record", {}, story("first"),
                   {"content_id": "incomplete", "central_conflict": "winter grain shortage"},
                   story("later")]
        candidates = [story("candidate"),
                      story("different", resolution="grain is lost in the flood"),
                      {"central_conflict": "winter grain shortage"}]
        index = CausalPremiseIndex(history)
        for candidate in candidates:
            self.assertEqual(index.match(candidate),
                             self._linear_reference(candidate, history))

    def test_index_normalizes_case_and_punctuation(self):
        prior = story("first", conflict="WINTER—GRAIN shortage!",
                      choice="Share, the last grain.", resolution="Both families survive together.")
        candidate = story("candidate", conflict="winter grain shortage",
                          choice="share the last grain", resolution="BOTH families survive together")
        self.assertEqual(CausalPremiseIndex([prior]).match(candidate)["matched_content_id"],
                         "first")

    def test_index_preserves_first_duplicate_arc(self):
        first, second = story("first"), story("second")
        self.assertEqual(CausalPremiseIndex([first, second]).match(story("candidate"))["matched_content_id"],
                         "first")

    def test_index_add_is_incremental_and_keeps_first_match(self):
        index = CausalPremiseIndex()
        candidate = story("candidate")
        self.assertIsNone(index.match(candidate))
        index.add(story("first"))
        self.assertEqual(index.match(candidate)["matched_content_id"], "first")
        index.add(story("second"))
        self.assertEqual(index.match(candidate)["matched_content_id"], "first")

    def test_triage_uses_index_without_falling_back_to_history_scan(self):
        with patch("astra_v2.story_editorial.causal_premise_match",
                   side_effect=AssertionError("triage must use its incremental index")):
            result = triage([story("second")], history=[story("first")])
        item = (result["ready_for_review"] + result["needs_work"])[0]
        self.assertEqual(item["causal_repeat_review"]["matched_content_id"], "first")
        self.assertEqual(item["causal_repeat_review"]["method"], "explicit_causal_arc_match")


if __name__ == "__main__":
    unittest.main()
