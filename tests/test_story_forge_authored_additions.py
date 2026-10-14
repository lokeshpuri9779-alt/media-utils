"""Regression checks for independently authored experimental stories."""
import unittest
from astra_v2.story_forge import catalog
from astra_v2.publication_quality import publication_rejection

EXPECTED = {
    "The Raccoon and the Midnight Bakery",
    "The Penguin and the Silent Trumpet",
    "The Beaver and the Floating Garden",
}

class AuthoredAdditionsTests(unittest.TestCase):
    def test_new_authored_stories_are_discoverable(self):
        stories = catalog(limit=10000)
        selected = [s for s in stories if s["title"] in EXPECTED]
        self.assertEqual({s["title"] for s in selected}, EXPECTED)
        for story in selected:
            self.assertEqual(story["kind"], "authored_causal_story")
            self.assertEqual(len(story["story_beats"]), 4)
            self.assertEqual([b["story_beat"] for b in story["story_beats"]],
                             ["reveal", "build", "twist", "payoff"])
            self.assertIsNone(publication_rejection(story))
            self.assertTrue(all(len(b["speech"].split()) >= 9 for b in story["story_beats"]))

if __name__ == "__main__":
    unittest.main()
