"""Character-region repetition review for rendered Studio preview stills.

This is a conservative editorial warning only; it never blocks publication.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from PIL import Image


def character_signature(image):
    """64-bit difference hash of the central character region."""
    if image.width < 64 or image.height < 64:
        raise ValueError("frame too small")
    box = (int(image.width * .34), int(image.height * .40),
           int(image.width * .66), int(image.height * .78))
    sample = image.crop(box).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(sample.getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return bits


def review_frames(paths, *, max_distance=4, min_pairs=2):
    if not 0 <= max_distance <= 64 or min_pairs < 1:
        raise ValueError("invalid visual review thresholds")
    frames = []
    for path in paths:
        with Image.open(path) as image:
            frames.append((Path(path).name, character_signature(image.convert("RGB"))))
    pairs = []
    for i, (left, a) in enumerate(frames):
        for right, b in frames[i + 1:]:
            distance = (a ^ b).bit_count()
            if distance <= max_distance:
                pairs.append({"left": left, "right": right, "distance": distance})
    return {
        "status": "review_required" if len(pairs) >= min_pairs else "no_repeat_warning",
        "sampled_frames": len(frames),
        "close_character_pairs": pairs,
        "threshold": {"max_hamming_distance": max_distance, "min_pairs": min_pairs},
        "enforcement": "diagnostic_only",
        "note": "Similar character-region composition is a review signal, not proof of duplicate content."
    }


if __name__ == "__main__":
    root = Path(sys.argv[1])
    paths = sorted(root.glob("scene_*.jpg"))
    if not paths:
        raise SystemExit("No scene_*.jpg preview stills found")
    report = review_frames(paths)
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "visual-reuse-review.json"
    output.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
