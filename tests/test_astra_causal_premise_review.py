import unittest

from astra_v2.causal_premise_review import causal_premise_match
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


if __name__ == "__main__":
    unittest.main()
