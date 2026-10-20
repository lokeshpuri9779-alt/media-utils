import unittest

from astra_v2.editorial_batch_preparation import prepare_batch


class EditorialBatchPreparationTests(unittest.TestCase):
    def test_batch_remains_unapproved(self):
        story = {"content_id": "one", "kind": "authored_causal_story",
                 "production_ready": True, "story_beats": []}
        result = prepare_batch({"stories": [story]})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["approved_count"], 0)
        self.assertFalse(result["publication_triggered"])
        self.assertFalse(result["stories"][0]["story"]["production_ready"])
        self.assertTrue(story["production_ready"])

    def test_rejects_duplicates_and_invalid_documents(self):
        story = {"content_id": "one", "story_beats": []}
        for document in ({}, {"stories": [story, story]}, {"stories": [None]}):
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    prepare_batch(document)


if __name__ == "__main__":
    unittest.main()
