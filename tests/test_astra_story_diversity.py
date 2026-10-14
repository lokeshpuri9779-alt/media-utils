import unittest
from astra_v2.story_diversity_audit import audit_history, similarity

def story(title, beats, actions):
    return {"title": title, "scenes": [
        {"narration": beat, "action": action}
        for beat, action in zip(beats, actions)
    ]}

class HistoryAuditTests(unittest.TestCase):
    def test_identical_story_rejected(self):
        s = story("A", ["A cat repairs a broken clock", "The cat celebrates"], ["repair", "celebrate"])
        result = audit_history([s], history=[s])
        self.assertEqual(result["near_duplicates"], 1)
        self.assertFalse(result["publication_allowed"])

    def test_distinct_story_accepted(self):
        a = story("A", ["A cat repairs a broken clock"], ["repair"])
        b = story("B", ["A dragon flies across a mountain"], ["fly"])
        self.assertEqual(audit_history([b], history=[a])["near_duplicates"], 0)

    def test_duplicate_inside_batch(self):
        s = story("A", ["The owl finds a telescope"], ["approach"])
        self.assertEqual(audit_history([s, s])["near_duplicates"], 1)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            audit_history([], threshold=1.2)

    def test_empty_story_fails_continuity(self):
        from astra_v2.story_diversity_audit import audit
        result = audit([{"title": "Empty", "scenes": []}])["results"][0]
        self.assertFalse(result["continuity_ok"])
        self.assertFalse(result["repair_sequence_ok"])

    def test_similarity_bounds(self):
        a = story("A", ["An owl flies"], ["fly"])
        b = story("B", ["A fox runs"], ["run"])
        self.assertTrue(0 <= similarity(a, b) <= 1)

if __name__ == "__main__":
    unittest.main()
