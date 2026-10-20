"""Protect semantic fingerprint-dominance pruning and tie evidence."""
import unittest

from astra_v2.semantic_candidate_index import SemanticCandidateIndex
from astra_v2.story_editorial import semantic_duplicate_match


def story(i, fp=None, speech=None):
    return {"content_id": str(i), "title": "Story " + str(i),
            "plot_fingerprint": fp,
            "story_beats": [{"speech": speech or ("shared token " + str(i))}]}


class FingerprintDominanceTests(unittest.TestCase):
    def test_exact_fingerprint_dominates_large_overlapping_history(self):
        history = [story(i, speech="shared token overlap " + str(i)) for i in range(300)]
        history.insert(41, story("first", fp="same", speech="shared token"))
        history.insert(220, story("second", fp="same", speech="shared token overlap"))
        query = story("query", fp="same", speech="shared token overlap")
        self.assertEqual(SemanticCandidateIndex(history).match(query),
                         semantic_duplicate_match(query, history))

    def test_no_fingerprint_match_retains_reference_ranking(self):
        history = [story(i, fp="other", speech="shared token overlap " + str(i))
                   for i in range(60)]
        query = story("query", fp="missing", speech="shared token overlap")
        self.assertEqual(SemanticCandidateIndex(history).match(query),
                         semantic_duplicate_match(query, history))

    def test_incremental_fingerprint_insert_and_ties(self):
        index = SemanticCandidateIndex()
        history = []
        for i in range(75):
            item = story(i, fp="same" if i % 9 == 0 else None)
            self.assertEqual(index.match(item), semantic_duplicate_match(item, history))
            index.add(item)
            history.append(item)


if __name__ == "__main__":
    unittest.main()
