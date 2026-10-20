"""Exact parity checks for posting-based narration novelty screening."""
import unittest

from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.shorts_novelty import tokens, story_text, structural_signature


def exhaustive(story, previous, threshold):
    fp = story.get("plot_fingerprint")
    sig = structural_signature(story)
    if fp and any(fp == item.get("plot_fingerprint") for item in previous):
        return True
    if sig is not None and any(sig == structural_signature(item) for item in previous):
        return True
    words = tokens(story_text(story))
    if not words:
        return False
    for prior in previous:
        other = tokens(story_text(prior))
        if other and 2 * min(len(words), len(other)) >= threshold * (len(words) + len(other)):
            if 2 * len(words & other) / (len(words) + len(other)) >= threshold:
                return True
    return False


class TestNoveltyPostings(unittest.TestCase):
    def test_exact_parity_across_thresholds_and_incremental_updates(self):
        corpus = [
            {"content_id": str(i), "title": " ".join(
                f"word{(i * 13 + j * 7) % 59}" for j in range(3 + i % 11)),
             "story_beats": [{"speech": " ".join(
                f"word{(i * 13 + j * 7) % 59}" for j in range(3 + i % 11))}]}
            for i in range(180)
        ]
        idx = NoveltyIndex()
        seen = []
        for story in corpus:
            for threshold in (0.25, 0.5, 0.72, 0.88, 1.0):
                self.assertEqual(idx.is_near_duplicate(story, threshold),
                                 exhaustive(story, seen, threshold))
            idx.add(story)
            seen.append(story)

    def test_fingerprint_and_structure_shortcuts(self):
        a = {"plot_fingerprint": "fixed", "title": "alpha"}
        b = {"plot_fingerprint": "fixed", "title": "unrelated"}
        idx = NoveltyIndex([a])
        self.assertTrue(idx.is_near_duplicate(b))


if __name__ == "__main__":
    unittest.main()
