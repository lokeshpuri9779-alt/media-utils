"""Compare indexed triage output against the unchanged exhaustive path."""
import unittest

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import triage


class IndexedTriageParityTests(unittest.TestCase):
    def test_full_review_payload_parity(self):
        history = [proposal(i) for i in range(30)]
        candidates = [proposal(i) for i in range(25, 95)]
        self.assertEqual(triage(candidates, history),
                         triage(candidates, history, use_semantic_index=True))

    def test_empty_and_repeated_proposals(self):
        stories = [proposal(i) for i in [1, 1, 2, 1, 7, 8, 7]]
        self.assertEqual(triage(stories),
                         triage(stories, use_semantic_index=True))


if __name__ == "__main__":
    unittest.main()
