"""An original CPU 2D floor-hatch reveal for the reviewed Mara pilot.

Only the Episode 1 'trace_cable' scene uses this stage geometry. It is not a
general scene generator, and even a successful render cannot establish video
semantic fidelity without an independent complete-MP4 review.
"""
from __future__ import annotations

import math
from PIL import ImageDraw
from astra_errors import CreativeReject


# The boarded trapdoor sits beside the visible cable end and the authored
# second radio (center 342, 1109). Keep all geometry in the middle scene stage.
OPENING = ((238, 1078), (468, 1078), (500, 1190), (217, 1190))
LIFTED_BOARD = ((166, 947), (249, 985), (225, 1185), (178, 1166))
WOOD = (106, 76, 57)
WOOD_GRAIN = (162, 122, 84)
VOID = (11, 24, 37)
STAIR = (76, 95, 110)


def _smooth(value):
    v = max(0.0, min(1.0, value))
    return v * v * (3.0 - 2.0 * v)


def floorboard_reveal_fraction(event):
    """Finite, gradual opening after the cable has been located."""
    if type(event) not in (int, float) or not math.isfinite(event) or not 0 <= event <= 1:
        raise CreativeReject("Invalid authored floor-hatch event")
    return _smooth((event - .08) / .67)


def floorboard_panel(progress):
    """Return panel corners; continuous opening keeps every frame deterministic."""
    v = floorboard_reveal_fraction(progress)
    return tuple((round(a[0] + (b[0] - a[0]) * v),
                  round(a[1] + (b[1] - a[1]) * v))
                 for a, b in zip(OPENING, LIFTED_BOARD))


def draw_floorboard_hatch(draw, event):
    """Expose a dark below-floor cavity and raised planks before radio reveal.

    This illustrates the scripted *opening*, not a claim that the whole hidden
    room, Mara's discovery, or cable routing were semantically verified.
    """
    if not isinstance(draw, ImageDraw.ImageDraw):
        raise CreativeReject("Floorboard reveal requires a Pillow canvas")
    fraction = floorboard_reveal_fraction(event)
    # The room below is actually occluded by the closed wooden panel at first.
    # The floor is slightly inset at the far end and wider toward the viewer.
    draw.polygon(OPENING, fill=VOID, outline=(172, 142, 101), width=7)
    # Solid side edges distinguish a recessed space from a flat black patch.
    draw.line(((239, 1079), (222, 1184)), fill=(72, 93, 113), width=8)
    draw.line(((469, 1079), (498, 1184)), fill=(72, 93, 113), width=8)
    for x0, y0, x1, y1 in (
        (267, 1131, 453, 1131), (249, 1167, 479, 1167)):
        draw.line(((x0, y0), (x1, y1)), fill=STAIR, width=5)
    # Hinged plank surface lifts to the left, revealing the lower-room steps.
    panel = floorboard_panel(event)
    draw.polygon(panel, fill=WOOD, outline=(207, 171, 117), width=8)
    draw.line((panel[0], panel[3]), fill=WOOD_GRAIN, width=5)
    draw.line((panel[1], panel[2]), fill=(69, 53, 48), width=5)
    # The hinge is a real fixed attachment to the floor, not a moving label.
    draw.ellipse((210, 1176, 234, 1200), fill=(164, 167, 162), outline=(49, 59, 71), width=3)
    return {"hatch_open_fraction": fraction, "verified_semantics": False}
