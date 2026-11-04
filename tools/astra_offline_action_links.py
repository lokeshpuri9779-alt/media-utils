"""Visible hand-to-prop connections in fixed ASTRA CPU preview scenes.

The actor grips reuse exact authored rig endpoints; a line to the scene's
physical prop makes the attempt/payoff less disconnected. Pixel checks inspect
the actually rendered line, including after lossy H.264 decoding. These cues
do NOT prove meaningful grasp mechanics, storyline accuracy, or visual quality.
No generative AI, assets, download, paid APIs, production or publication.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw

from tools.astra_offline_character_rig import SIZE, actor_grip_position

LINK_COLOR = (244, 86, 41)
LINE_WIDTH = 6
ACTION_STAGES = (1, 3)
CASES = ("glasshouse-sunshade", "footbridge-ducklings", "moon-mirror-garden")


def connection_path(case_id: str, stage: int,
                    progress: float) -> list[tuple[int, int]]:
    """Shared deterministic attachment geometry; fail closed off-catalog."""
    if case_id not in CASES or type(stage) is not int or stage not in ACTION_STAGES:
        raise ValueError("unsupported connection action")
    if (not isinstance(progress, (int, float)) or
        not math.isfinite(progress) or not 0 <= progress <= 1):
        raise ValueError("invalid connection progress")
    grip = actor_grip_position(case_id, stage, progress)
    if case_id == "glasshouse-sunshade":
        travel = int((125 if stage == 1 else 231) * progress)
        edge = 48 + 18 + travel
        return [grip, (104, 45), (edge, 75)]
    if case_id == "footbridge-ducklings":
        # Beaver holds plank's front edge, then pulls reed-rope toward
        # the left bridge post. The final anchor is above duckling heads.
        return [grip, (133, 107) if stage == 1 else (80, 73)]
    # Moth keeper physically reaches the mirror handle/screw.
    return [grip, (245, 68) if stage == 1 else (259, 77)]


def render_action_link(case_id: str, stage: int, progress: float) -> Image.Image:
    if case_id not in CASES or type(stage) is not int or not 0 <= stage <= 3:
        raise ValueError("unknown action link scene")
    if (not isinstance(progress, (int, float)) or
        not math.isfinite(progress) or not 0 <= progress <= 1):
        raise ValueError("invalid action link progress")
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    if stage not in ACTION_STAGES:
        return layer
    path = connection_path(case_id, stage, progress)
    draw = ImageDraw.Draw(layer)
    draw.line(path, fill=(*LINK_COLOR, 255), width=LINE_WIDTH, joint="curve")
    for x, y in (path[0], path[-1]):
        draw.ellipse((x-4, y-4, x+4, y+4), fill=(*LINK_COLOR, 255))
    return layer


def _count_color_near(frame: Image.Image, xy: tuple[int, int]) -> int:
    if not isinstance(frame, Image.Image) or frame.mode != "RGB" or frame.size != SIZE:
        raise ValueError("expected actual 320x180 RGB frame")
    x, y = xy
    if not 6 <= x < SIZE[0]-6 or not 34 <= y < 154:
        raise ValueError("expected connection midpoint inside action area")
    crop = frame.crop((x-5, y-5, x+6, y+6))
    return sum(1 for p in crop.getdata()
               if all(abs(p[i] - LINK_COLOR[i]) <= 62 for i in range(3)))


def audit_action_link(case_id: str, stage: int, progress: float,
                      frame: Image.Image) -> dict:
    """Look for two colored contact points along the expected action path."""
    path = connection_path(case_id, stage, progress)
    segments = []
    for first, last in zip(path, path[1:]):
        midpoint = (round((first[0]+last[0])/2),
                    round((first[1]+last[1])/2))
        count = _count_color_near(frame, midpoint)
        segments.append({
            "sample_center": list(midpoint),
            "matching_pixels": count,
            "passed": count >= 6,
        })
    passed = all(s["passed"] for s in segments)
    return {
        "case_id": case_id,
        "stage": ["setup", "attempt", "setback", "payoff"][stage],
        "audit_type": "fixed_grip_to_prop_colored_segments_only",
        "segments": segments,
        "passed": passed,
        "grip_is_exact_actor_rig_endpoint": True,
        "prop_interaction_semantics": "not_verified",
        "manual_visual_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
