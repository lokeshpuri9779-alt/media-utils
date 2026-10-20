"""Indexed near-duplicate screening for large editorial proposal inventories.

Exact identities use hash lookups. Narration comparisons remain conservative:
all previous stories are checked, preserving the existing threshold behavior.
"""
from collections import defaultdict

from astra_v2.shorts_novelty import tokens, story_text, structural_signature


class NoveltyIndex:
    def __init__(self, previous=()):
        self.fingerprints = set()
        self.structures = set()
        self.token_sets = []
        self.token_postings = defaultdict(set)
        for story in previous:
            self.add(story)

    def add(self, story):
        if not isinstance(story, dict):
            return
        fingerprint = story.get("plot_fingerprint")
        if fingerprint:
            self.fingerprints.add(fingerprint)
        signature = structural_signature(story)
        if signature is not None:
            self.structures.add(signature)
        word_set = tokens(story_text(story))
        position = len(self.token_sets)
        self.token_sets.append(word_set)
        for word in word_set:
            self.token_postings[word].add(position)

    def is_near_duplicate(self, candidate, threshold=0.88):
        if not 0 < threshold <= 1:
            raise ValueError("Invalid near-duplicate threshold")
        fingerprint = candidate.get("plot_fingerprint")
        signature = structural_signature(candidate)
        if fingerprint and fingerprint in self.fingerprints:
            return True
        if signature is not None and signature in self.structures:
            return True
        words = tokens(story_text(candidate))
        if not words:
            return False
        count = len(words)
        # Zero-overlap stories cannot reach a positive Dice threshold.
        # Postings preserve exact decisions while avoiding unrelated stories.
        positions = set()
        for word in words:
            positions.update(self.token_postings.get(word, ()))
        for position in positions:
            other = self.token_sets[position]
            if not other:
                continue
            # A Dice score >= threshold is impossible if sizes differ too much.
            size = len(other)
            if 2 * min(count, size) < threshold * (count + size):
                continue
            if 2 * len(words & other) / (count + size) >= threshold:
                return True
        return False
