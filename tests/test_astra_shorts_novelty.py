import unittest
from astra_v2.shorts_novelty import similarity, is_near_duplicate


def story(speech, fingerprint=""):
    return {"plot_fingerprint": fingerprint, "story_beats": [{"speech": speech}]}


class ShortsNoveltyTests(unittest.TestCase):
    def test_exact_fingerprint(self):
        self.assertTrue(is_near_duplicate(story("hello", "abc"), [story("different", "abc")]))

    def test_near_identical_narration(self):
        a = story("The little robot found a broken bridge and repaired it before sunrise.")
        b = story("The little robot found a damaged bridge and repaired it before sunrise.")
        self.assertTrue(is_near_duplicate(a, [b]))

    def test_distinct_narratives(self):
        a = story("An astronaut discovered a secret map hidden inside Saturn's rings.")
        b = story("A young gardener planted seeds beside the village river.")
        self.assertFalse(is_near_duplicate(a, [b]))

    def test_missing_narration_does_not_match(self):
        self.assertEqual(similarity(story(""), story("")), 0.0)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            is_near_duplicate(story("x"), [], threshold=0)


if __name__ == "__main__":
    unittest.main()
