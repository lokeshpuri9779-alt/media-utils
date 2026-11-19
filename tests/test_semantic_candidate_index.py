"""Parity tests for the opt-in semantic inverted index."""
import unittest

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.semantic_candidate_index import SemanticCandidateIndex
from astra_v2.story_editorial import semantic_duplicate_match, triage


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

    def test_indexed_triage_matches_reference_and_never_approves(self):
        stories = [proposal(i) for i in range(125)]
        stories += [dict(stories[7], content_id="repeat-seven")]
        reference = triage(stories)
        indexed = triage(stories, use_semantic_index=True)
        self.assertEqual(indexed, reference)
        self.assertTrue(all(item["publication_blocked"] for item in
                            indexed["ready_for_review"] + indexed["needs_work"]))
        self.assertTrue(all(not story["production_ready"] for story in stories))

    def test_dense_common_word_postings_preserve_reference_scores(self):
        history = []
        for i in range(240):
            words = ["the village gathered near the river", "a lantern guided the neighbors"]
            words.append(f"distinct premise token{i} mechanism{i % 13}")
            if i % 4 == 0:
                words.append("shared bridge repair choice")
            history.append({
                "content_id": f"history-{i}",
                "title": f"Story {i}",
                "plot_fingerprint": f"fingerprint-{i}",
                "story_beats": [{"speech": " ".join(words)}],
            })
        index = SemanticCandidateIndex(history)
        candidates = [
            {"content_id": "candidate-a", "title": "Candidate A",
             "story_beats": [{"speech": "the village gathered near the river "
                                       "a lantern guided the neighbors "
                                       "distinct premise token77 mechanism12"}]},
            {"content_id": "candidate-b", "title": "Candidate B",
             "story_beats": [{"speech": "the village gathered near the river "
                                       "shared bridge repair choice "
                                       "distinct premise token999 mechanism4"}]},
            {"content_id": "candidate-c", "title": "Candidate C",
             "story_beats": [{"speech": "completely unrelated cobalt mountain observatory"}]},
        ]
        for candidate in candidates:
            self.assertEqual(index.match(candidate),
                             semantic_duplicate_match(candidate, history))

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            SemanticCandidateIndex().match(proposal(0), 0)


if __name__ == "__main__":
    unittest.main()