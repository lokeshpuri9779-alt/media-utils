"""Articulated 2D character silhouettes for isolated ASTRA CPU preview scenes.

Explicit hand-authored character rigs and simple key poses; NOT AI models,
3D assets, character recognition, semantic action verification or release art.
Every pose includes a fixed-color identity mark for a bounded pixel audit.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

SIZE = (320, 180)
PROFILES = {
    "glasshouse-sunshade": {
        "identity": "mina_beetle",
        "mark": (246, 191, 77),
        "roi": (10, 78, 118, 159),
        "min_marker_pixels": 20,
    },
    "footbridge-ducklings": {
        "identity": "beaver_builder",
        "mark": (44, 198, 195),
        "roi": (10, 62, 120, 154),
        "min_marker_pixels": 20,
    },
    "moon-mirror-garden": {
        "identity": "moth_keeper",
        "mark": (63, 235, 220),
        "roi": (20, 66, 250, 146),
        "min_marker_pixels": 20,
    },
}


def _disc(d: ImageDraw.ImageDraw, x: float, y: float, r: int,
          color: tuple[int, int, int]) -> None:
    d.ellipse((int(x-r), int(y-r), int(x+r), int(y+r)), fill=(*color, 255))


def _line(d: ImageDraw.ImageDraw, a: tuple[float, float],
          b: tuple[float, float], color: tuple[int, int, int], width: int = 2) -> None:
    d.line((*map(int, a), *map(int, b)), fill=(*color, 255), width=width)


def _beetle(d: ImageDraw.ImageDraw, stage: int, t: float, mark) -> None:
    x = [30 + 9*t, 40 + 5*t, 44 - 8*t, 38 + 9*t][stage]
    cy = 142
    # Six visible legs and a two-part green beetle body, each stage reuses
    # the same head proportions and the same gold shell mark.
    for offset in (-8, -2, 5):
        _line(d, (x+offset, cy+7), (x+offset-9, cy+13),
              (37, 92, 66), 2)
        _line(d, (x+offset+4, cy+8), (x+offset+11, cy+14),
              (37, 92, 66), 2)
    _disc(d, x, cy+4, 12, (39, 121, 91))
    _disc(d, x+12, cy-2, 7, (64, 156, 106))
    _disc(d, x+15, cy-4, 2, (20, 31, 33))
    _line(d, (x+13, cy-8), (x+17, cy-16), (109, 72, 48), 2)
    _line(d, (x+16, cy-8), (x+22, cy-17), (109, 72, 48), 2)
    _disc(d, x+17, cy-16, 2, (234, 165, 74))
    _disc(d, x+22, cy-17, 2, (234, 165, 74))
    # Mechanical intervention: facing hand and foreleg change by beat.
    reach = [(x+18, cy-4-9*t),
             (x+24+20*t, cy-22-23*t),
             (x+21-7*t, cy-35+12*t),
             (x+25+12*t, cy-22-27*t)][stage]
    _line(d, (x+12, cy+2), reach, (23, 87, 64), 3)
    _disc(d, *reach, 3, (57, 151, 105))
    _disc(d, x-4, cy+3, 4, mark)
    _line(d, (x-6, cy-2), (x-1, cy+8), (25, 71, 57), 1)


def _beaver(d: ImageDraw.ImageDraw, stage: int, t: float, mark) -> None:
    x = [41 + 6*t, 44 + 5*t, 49 - 7*t, 42 + 9*t][stage]
    y = 99
    d.ellipse((int(x-36), int(y+2), int(x-10), int(y+15)),
              fill=(94, 62, 46, 255))
    _line(d, (x-24, y+7), (x-33, y+9), (69, 43, 36), 2)
    d.ellipse((int(x-21), int(y-12), int(x+13), int(y+16)),
              fill=(118, 77, 51, 255))
    _disc(d, x+14, y-8, 9, (153, 99, 63))
    _disc(d, x+10, y-16, 3, (114, 67, 47))
    _disc(d, x+18, y-10, 2, (26, 31, 33))
    _disc(d, x+22, y-5, 2, (60, 38, 33))
    for dx in (-12, 5):
        _line(d, (x+dx, y+12), (x+dx+2, y+18),
              (77, 51, 39), 3)
    # An articulated front paw reaches toward the loose bridge plank.
    end = [(x+22+2*t, y+5-4*t),
           (x+25+24*t, y+6-5*t),
           (x+36-19*t, y+11+12*t),
           (x+25+16*t, y+3-5*t)][stage]
    _line(d, (x+10, y+8), end, (95, 61, 43), 4)
    _disc(d, *end, 4, (147, 90, 59))
    # Same blue scarf on each scene is a stronger continuity anchor than
    # a bare geometric circle, but is NOT a learned identity evaluation.
    d.polygon([(int(x+1), y-2), (int(x+13), y),
               (int(x+12), y+6), (int(x+1), y+4)],
              fill=(*mark, 255))


def _moth(d: ImageDraw.ImageDraw, stage: int, t: float, mark) -> None:
    x = [40+10*t, 50+158*t, 208-8*t, 204+8*t][stage]
    y = 103
    wing = 9 + 7*(0.5 + 0.5*math.sin(2*math.pi*2.5*t))
    # Paired swept wings (not just a moving center point), rigid head
    # proportions and the same glowing cyan body badge in all four beats.
    d.ellipse((int(x-wing-11), int(y-14-wing/3),
               int(x-2), int(y+7)),
              fill=(167, 133, 203, 255))
    d.ellipse((int(x+2), int(y-14-wing/3),
               int(x+wing+11), int(y+7)),
              fill=(167, 133, 203, 255))
    _disc(d, x, y+2, 10, (121, 92, 160))
    _disc(d, x, y-9, 6, (148, 118, 183))
    _line(d, (x-3, y-14), (x-7, y-21), (195, 182, 205), 2)
    _line(d, (x+3, y-14), (x+7, y-21), (195, 182, 205), 2)
    _disc(d, x-3, y-10, 2, (20, 27, 41))
    _disc(d, x+3, y-10, 2, (20, 27, 41))
    # Linen apron, cyan badge and reach toward the bracket or mirror.
    d.rectangle((int(x-5), y-1, int(x+5), y+12), fill=(222, 208, 192, 255))
    end = [(x+9, y+4-5*t),
           (x+19+7*t, y-4-14*t),
           (x+10-8*t, y-12+15*t),
           (x+20+7*t, y-4-13*t)][stage]
    _line(d, (x+5, y+4), end, (151, 112, 187), 3)
    _disc(d, *end, 3, (179, 136, 197))
    _disc(d, x, y+5, 4, mark)


def render_actor_layer(case_id: str, stage: int,
                       progress: float) -> Image.Image:
    """Draw one recognized consistent character on a transparent canvas."""
    if case_id not in PROFILES:
        raise ValueError("unknown reference-character rig")
    if type(stage) is not int or stage not in range(4):
        raise ValueError("invalid rig stage")
    if not isinstance(progress, (int, float)) or not math.isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError("invalid rig progress")
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    mark = PROFILES[case_id]["mark"]
    if case_id == "glasshouse-sunshade":
        _beetle(draw, stage, progress, mark)
    elif case_id == "footbridge-ducklings":
        _beaver(draw, stage, progress, mark)
    else:
        _moth(draw, stage, progress, mark)
    return layer


def marker_pixel_count(frame: Image.Image, case_id: str) -> int:
    """Count a fixed character badge color inside its known region."""
    if case_id not in PROFILES:
        raise ValueError("unsupported character marker profile")
    if not isinstance(frame, Image.Image) or frame.size != SIZE or frame.mode != "RGB":
        raise ValueError("invalid RGB scene frame for character audit")
    info = PROFILES[case_id]
    mark = info["mark"]
    return sum(1 for p in frame.crop(info["roi"]).getdata()
               if all(abs(p[i] - mark[i]) <= 22 for i in range(3)))


def audit_character_presence(case_id: str, scenes: list[Image.Image]) -> dict:
    """Detect fixed badge visibility in all four beats, never approve video."""
    if case_id not in PROFILES or not isinstance(scenes, list) or len(scenes) != 4:
        raise ValueError("unknown or incomplete character continuity profile")
    counts = [marker_pixel_count(scene, case_id) for scene in scenes]
    minimum = PROFILES[case_id]["min_marker_pixels"]
    passed = all(value >= minimum for value in counts)
    return {
        "case_id": case_id,
        "character_id": PROFILES[case_id]["identity"],
        "presence_cue": "fixed_color_emblem_pixels_only",
        "marker_pixel_counts": counts,
        "minimum_per_beat": minimum,
        "passed": passed,
        "character_identity_semantics": "not_verified",
        "character_art_quality": "not_verified",
        "manual_visual_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
