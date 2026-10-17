"""Indexed near-duplicate screening for large editorial proposal inventories.

Exact identities use hash lookups. Narration comparisons remain conservative:
all previous stories are checked, preserving the existing threshold behavior.
"""
from astra_v2.shorts_novelty import tokens, story_text, structural_signature


class NoveltyIndex:
    def __init__(self, previous=()):
        self.fingerprints = set()
        self.structures = set()
        self.token_sets = []
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
        self.token_sets.append(tokens(story_text(story)))

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
        for other in self.token_sets:
            if not other:
                continue
            # A Dice score >= threshold is impossible if sizes differ too much.
            size = len(other)
            if 2 * min(count, size) < threshold * (count + size):
                continue
            if 2 * len(words & other) / (count + size) >= threshold:
                return True
        return False
