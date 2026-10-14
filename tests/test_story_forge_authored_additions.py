"""Regression checks for independently authored experimental stories."""
import unittest
from astra_v2.story_forge import catalog
from astra_v2.publication_quality import publication_rejection

EXPECTED = {
    "The Raccoon and the Midnight Bakery",
    "The Penguin and the Silent Trumpet",
    "The Beaver and the Floating Garden",
    "The Mole and the Lantern Path",
    "The Otter and the Paper Boat Race",
    "The Badger and the Vanishing Music",
    "The Fox and the Festival of Shadows",
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

    def test_used_story_is_not_selected_again(self):
        stories = [s for s in catalog(limit=10000) if s["title"] in EXPECTED]
        self.assertEqual(len(stories), len(EXPECTED))
        ids = [s["content_id"] for s in stories]
        fingerprints = [s["plot_fingerprint"] for s in stories]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(set(fingerprints)), len(fingerprints))
        for story in stories:
            excluded = catalog(excluded_ids={story["content_id"]}, limit=10000)
            self.assertNotIn(story["content_id"], {s["content_id"] for s in excluded})
            excluded = catalog(excluded_plot_hashes={story["plot_fingerprint"]}, limit=10000)
            self.assertNotIn(story["content_id"], {s["content_id"] for s in excluded})

if __name__ == "__main__":
    unittest.main()
