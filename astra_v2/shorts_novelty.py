"""Conservative near-duplicate detection for ASTRA Shorts.

Exact fingerprint protection remains authoritative. Similarity checks are
additive and deliberately require substantial shared narration vocabulary.
"""
import re


def tokens(value):
    return set(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def story_text(story):
    beats = story.get("story_beats") or []
    return " ".join(str(beat.get("speech") or "") for beat in beats if isinstance(beat, dict))


def similarity(a, b):
    """Sørensen-Dice similarity of narration word sets."""
    left, right = tokens(story_text(a)), tokens(story_text(b))
    if not left or not right:
        return 0.0
    return 2 * len(left & right) / (len(left) + len(right))


def is_near_duplicate(candidate, previous, threshold=0.88):
    """Require a high threshold to avoid rejecting shared genre vocabulary."""
    if not 0 < threshold <= 1:
        raise ValueError("Invalid near-duplicate threshold")
    fingerprint = candidate.get("plot_fingerprint")
    for item in previous:
        if not isinstance(item, dict):
            continue
        if fingerprint and fingerprint == item.get("plot_fingerprint"):
            return True
        if similarity(candidate, item) >= threshold:
            return True
    return False
