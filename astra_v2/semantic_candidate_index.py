"""Experimental exact-candidate semantic index; not connected to publishing.

Only candidates sharing signature tokens, narration words, or a fingerprint
can produce a positive semantic match at the standard positive thresholds.
Preserve historical order when forwarding candidates to the reference scorer.
"""
from collections import defaultdict

from astra_v2.story_editorial import _semantic_features, _semantic_match_features


class SemanticCandidateIndex:
    def __init__(self, history=()):
        self.items = []
        self.signature_postings = defaultdict(set)
        self.word_postings = defaultdict(set)
        self.fingerprint_postings = defaultdict(set)
        for story in history:
            if isinstance(story, dict):
                self.add(story)

    def add(self, story):
        features = _semantic_features(story)
        position = len(self.items)
        self.items.append((story, features))
        signature, words, fingerprint = features
        for token in signature:
            self.signature_postings[token].add(position)
        for token in words:
            self.word_postings[token].add(position)
        if fingerprint:
            self.fingerprint_postings[fingerprint].add(position)

    def match(self, story, threshold=0.72):
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be positive and at most one")
        features = _semantic_features(story)
        signature, words, fingerprint = features
        positions = set()
        for token in signature:
            positions.update(self.signature_postings.get(token, ()))
        for token in words:
            positions.update(self.word_postings.get(token, ()))
        if fingerprint:
            positions.update(self.fingerprint_postings.get(fingerprint, ()))
        # A fingerprint match outranks every non-fingerprint candidate in the
        # reference lexicographic score. Restrict to those matches when present.
        # Do not threshold-prune other candidates: the reference scorer selects
        # its best match BEFORE testing thresholds, so pruning can change output.
        if fingerprint:
            exact_positions = self.fingerprint_postings.get(fingerprint, ())
            if exact_positions:
                positions = exact_positions
        # Preserve historical order and reference evidence format.
        candidates = [self.items[i] for i in sorted(positions)]
        return _semantic_match_features(story, features, candidates, threshold)
