import unittest
from experimental.story_development import development_batch, develop
from experimental.story_draft_bank import draft_bank
from astra_v2.publication_quality import publication_rejection

class StoryDevelopmentTests(unittest.TestCase):
    def test_develop_all_without_approval(self):
        results=development_batch()
        self.assertEqual(len(results),1024)
        self.assertEqual(len({x["content_id"] for x in results}),1024)
        for story in results:
            self.assertEqual([b["role"] for b in story["story_beats"]],
                             ["reveal","build","twist","payoff"])
            self.assertEqual(len(story["story_beats"]),4)
            self.assertFalse(story["production_ready"])
            self.assertIsNotNone(publication_rejection(story))
    def test_unknown_conflict_rejected(self):
        draft=dict(draft_bank()[0],conflict="unrecognized")
        with self.assertRaises(ValueError):
            develop(draft)
if __name__=="__main__":unittest.main()
