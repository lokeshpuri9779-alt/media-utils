"""Experimental exact-candidate semantic index; not connected to publishing.

Only candidates sharing signature tokens, narration words, or a fingerprint
can produce a positive semantic match at the standard positive thresholds.
Preserve historical order and the reference scorer's rounded-score behavior.
"""
from collections import Counter, defaultdict

from astra_v2.story_editorial import _semantic_features


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

        # Count shared terms while traversing postings once. The previous
        # implementation built a candidate union and then repeatedly
        # intersected Python sets for every candidate, which was costly when
        # common narration words produced dense postings.
        signature_overlaps = Counter()
        word_overlaps = Counter()
        for token in signature:
            signature_overlaps.update(self.signature_postings.get(token, ()))
        for token in words:
            word_overlaps.update(self.word_postings.get(token, ()))

        positions = set(signature_overlaps) | set(word_overlaps)
        if fingerprint:
            exact_positions = self.fingerprint_postings.get(fingerprint, ())
            if exact_positions:
                # Fingerprint equality outranks every non-fingerprint score.
                positions = exact_positions
        if not positions:
            return None

        signature_size = len(signature)
        words_size = len(words)
        best = None
        best_score = None
        for position in sorted(positions):
            prior, _ = self.items[position]
            shared_signature = signature_overlaps.get(position, 0)
            union_size = signature_size + len(self.items[position][1][0]) - shared_signature
            jaccard = shared_signature / union_size if union_size else 0.0
            prior_words_size = len(self.items[position][1][1])
            shared_words = word_overlaps.get(position, 0)
            dice = (2 * shared_words / (words_size + prior_words_size)
                    if words and prior_words_size else 0.0)
            fingerprint_match = bool(fingerprint and
                                     fingerprint == self.items[position][1][2])
            score = (fingerprint_match, jaccard, dice)
            # Match the reference scorer exactly: it compares raw current
            # scores against the rounded incumbent evidence tuple.
            if best_score is None or score > best_score:
                best_score = (fingerprint_match, round(jaccard, 4), round(dice, 4))
                best = {
                    "matched_content_id": prior.get("content_id"),
                    "matched_title": prior.get("title"),
                    "jaccard_similarity": round(jaccard, 4),
                    "dice_similarity": round(dice, 4),
                    "jaccard_threshold": threshold,
                    "dice_threshold": 0.88,
                    "plot_fingerprint_match": fingerprint_match,
                    "method": "plot_fingerprint_and_narration_similarity",
                }
        triggered = (best["plot_fingerprint_match"] or
                     best["jaccard_similarity"] >= threshold or
                     best["dice_similarity"] >= 0.88)
        return best if triggered else None
