import unittest

from astra_v2.editorial_preparation import prepare_for_editorial_review


class EditorialPreparationTests(unittest.TestCase):
    def test_does_not_mutate_or_approve(self):
        proposal = {"content_id": "candidate-1", "kind": "authored_causal_story",
                    "production_ready": True, "story_beats": []}
        result = prepare_for_editorial_review(proposal)
        self.assertTrue(proposal["production_ready"])
        self.assertFalse(result["story"]["production_ready"])
        self.assertEqual(result["story"]["kind"], "unreviewed_causal_draft")
        self.assertTrue(result["requires_explicit_editorial_approval"])
        self.assertFalse(result["publication_triggered"])
        self.assertIn("four_beats_required", result["preparation_issues"])

    def test_rejects_invalid_proposal(self):
        for proposal in (None, {}, {"content_id": ""}):
            with self.subTest(proposal=proposal):
                with self.assertRaises(ValueError):
                    prepare_for_editorial_review(proposal)


if __name__ == "__main__":
    unittest.main()
