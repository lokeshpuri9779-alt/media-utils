"""Offline, scene-specific visual outcome negative controls for ASTRA previews.

This module checks a few fixed pixel regions and approximate colors only.
It CANNOT establish story semantics, realism, human preference, camera quality,
or suitability for publishing. A passed cue is limited to these known
assistant-authored procedural scenes; unknown scene IDs fail closed.
"""
from __future__ import annotations

from PIL import Image

SIZE = (320, 180)
# Regions never include moving captions or bottom annotation bar.
# (region, target RGB, tolerance per channel, max count at initial frame,
#  minimum count at completed payoff frame)
CUES = {
    "glasshouse-sunshade": {
        "canopy_over_seedlings": ((125, 55, 205, 69), (50, 118, 128), 35, 20, 250),
        "shaded_seedlings": ((130, 105, 170, 118), (29, 92, 54), 20, 5, 30),
    },
    "footbridge-ducklings": {
        "plank_across_gap": ((125, 106, 205, 117), (147, 96, 65), 35, 20, 200),
        "ducklings_on_safe_bank": ((35, 85, 96, 111), (248, 220, 88), 35, 20, 80),
    },
    "moon-mirror-garden": {
        "beam_on_flowerbed": ((130, 96, 170, 122), (210, 199, 148), 35, 20, 100),
        "open_pink_petals": ((80, 95, 210, 122), (235, 163, 228), 35, 20, 100),
    },
}


def cue_pixel_count(image: Image.Image, region: tuple[int, int, int, int],
                    rgb: tuple[int, int, int], tolerance: int) -> int:
    """Count approximate-color pixels only within a known, bounded scene ROI."""
    if not isinstance(image, Image.Image) or image.mode != "RGB" or image.size != SIZE:
        raise ValueError("unexpected 320x180 RGB decoded preview")
    x0, y0, x1, y1 = region
    if not 0 <= x0 < x1 <= SIZE[0] or not 28 <= y0 < y1 <= 160:
        raise ValueError("cue ROI must exclude captions")
    if not 0 <= tolerance <= 45:
        raise ValueError("invalid cue tolerance")
    return sum(
        1 for pixel in image.crop(region).getdata()
        if all(abs(pixel[i] - rgb[i]) <= tolerance for i in range(3))
    )


def audit_visible_outcome(case_id: str, first: Image.Image,
                          last: Image.Image) -> dict:
    """Reject missing explicit visual cues; never claim narrative verification."""
    if case_id not in CUES:
        raise ValueError("unsupported visual outcome profile")
    checks = {}
    for name, (region, color, tolerance, baseline_max, payoff_min) in CUES[case_id].items():
        baseline = cue_pixel_count(first, region, color, tolerance)
        payoff = cue_pixel_count(last, region, color, tolerance)
        checks[name] = {
            "baseline_match_pixels": baseline,
            "payoff_match_pixels": payoff,
            "baseline_max": baseline_max,
            "payoff_min": payoff_min,
            "passed": baseline <= baseline_max and payoff >= payoff_min,
        }
    failed = sorted(name for name, value in checks.items() if not value["passed"])
    return {
        "case_id": case_id,
        "audit_type": "procedural_palette_and_location_cues_only",
        "passed": not failed,
        "failed_cues": failed,
        "checks": checks,
        "story_semantics": "not_verified",
        "human_visual_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
