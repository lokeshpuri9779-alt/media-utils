"""Conservative perceptual diversity checks for rendered ASTRA frames.

Use on comparable story-stage frames; do not compare title cards or captions.
A match is a review signal, not automatic proof of duplicate storytelling.
"""
from __future__ import annotations

from PIL import Image, ImageChops, ImageStat


def stage_signature(image):
    """64-bit perceptual difference hash of the central illustrated stage."""
    if image.width < 64 or image.height < 64:
        raise ValueError("frame too small")
    # Normalize stage geometry to avoid mistaking identical sidebars for art.
    box = (int(image.width*.12), int(image.height*.30),
           int(image.width*.88), int(image.height*.72))
    sample = image.crop(box).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(sample.getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(pixels[y*9+x] > pixels[y*9+x+1])
    return bits


def hamming_distance(a, b):
    return (int(a) ^ int(b)).bit_count()


def suspicious_reuse(current_frames, prior_frames, *, max_distance=3, min_matches=2):
    """Require multiple close matches, reducing single-frame false positives."""
    if not 0 <= max_distance <= 64 or min_matches < 2:
        raise ValueError("invalid visual reuse thresholds")
    current = [stage_signature(frame) for frame in current_frames]
    prior = [stage_signature(frame) for frame in prior_frames]
    if len(current) < min_matches or len(prior) < min_matches:
        return False
    # Distinct matched reference frames prevent one stock still from
    # counting as multiple independent matching scenes.
    used = set()
    matched = 0
    for value in current:
        for idx, reference in enumerate(prior):
            if idx not in used and hamming_distance(value, reference) <= max_distance:
                used.add(idx)
                matched += 1
                break
    return matched >= min_matches
