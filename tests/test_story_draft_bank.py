import unittest
from experimental.story_draft_bank import draft_bank
from astra_v2.publication_quality import publication_rejection

class DraftBankTests(unittest.TestCase):
    def test_1024_unique_drafts(self):
        drafts=draft_bank()
        self.assertEqual(len(drafts),1024)
        self.assertEqual(len({d["content_id"] for d in drafts}),1024)
        self.assertEqual(len({d["premise"] for d in drafts}),1024)
        self.assertEqual(len({d["title"] for d in drafts}),1024)
    def test_not_publishable(self):
        for d in draft_bank():
            self.assertFalse(d["production_ready"])
            self.assertFalse(d["publication_allowed"])
            self.assertIsNotNone(publication_rejection(d))
if __name__=="__main__":unittest.main()
