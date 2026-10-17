"""Parity tests for the opt-in semantic inverted index."""
import unittest

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.semantic_candidate_index import SemanticCandidateIndex
from astra_v2.story_editorial import semantic_duplicate_match


class SemanticCandidateIndexTests(unittest.TestCase):
    def test_historical_and_sequential_parity(self):
        history = [proposal(i) for i in range(90)]
        index = SemanticCandidateIndex(history)
        for i in [0, 1, 12, 44, 89, 90, 120, 500]:
            self.assertEqual(index.match(proposal(i)),
                             semantic_duplicate_match(proposal(i), history))
        for i in range(90, 125):
            story = proposal(i)
            self.assertEqual(index.match(story),
                             semantic_duplicate_match(story, history))
            history.append(story)
            index.add(story)

    def test_disjoint_and_fingerprint_match(self):
        first = {"content_id": "first", "title": "First",
                 "plot_fingerprint": "same",
                 "story_beats": [{"speech": "violet lantern"}]}
        second = {"content_id": "second", "title": "Second",
                  "plot_fingerprint": "same",
                  "story_beats": [{"speech": "orange river"}]}
        index = SemanticCandidateIndex([first])
        self.assertEqual(index.match(second),
                         semantic_duplicate_match(second, [first]))
        unrelated = {"content_id": "third",
                     "story_beats": [{"speech": "silver meadow"}]}
        self.assertIsNone(index.match(unrelated))

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            SemanticCandidateIndex().match(proposal(0), 0)


if __name__ == "__main__":
    unittest.main()
