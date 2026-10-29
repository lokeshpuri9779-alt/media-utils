import unittest
from story_diagnostics import from_story
from advisory_adapter import analyze

class StoryDiagnosticsTests(unittest.TestCase):
    def test_flat_story(self):
        data = from_story({"hook":"Why did the lighthouse disappear?", "title":"The Missing Lighthouse", "thumbnail_text":"GONE"})
        self.assertEqual(data["hook"], "Why did the lighthouse disappear?")
        self.assertTrue(analyze(data)["advisory_only"])
    def test_nested_story(self):
        data = from_story({"script":{"opening":"Nobody returned from the island."},"metadata":{"youtube_title":"The Island","thumbnail_text":"NO RETURN"}})
        self.assertEqual(data["title"], "The Island")
        self.assertEqual(data["thumbnail"], "NO RETURN")
    def test_missing(self):
        self.assertNotIn("hook", analyze(from_story({})))
    def test_bad_story(self):
        with self.assertRaises(ValueError):
            from_story([])

if __name__ == "__main__":
    unittest.main()
