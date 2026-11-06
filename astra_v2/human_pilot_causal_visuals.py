"""Original, deterministic Episode 1 cause-and-effect scene objects.

These 2D visual cues make the scripted unplug, city outage and staircase
concrete. They are NOT evidence that the complete encoded video depicts
the authored actions: an independent full-video review remains required.
"""
from __future__ import annotations

import math
from PIL import ImageDraw
from astra_errors import CreativeReject

NIGHT = (10, 24, 40)
BUILDING = (33, 50, 69)
BUILDING_EDGE = (90, 121, 141)
LIGHT = (251, 205, 114)
DARK_WINDOW = (24, 37, 55)
COPPER = (205, 158, 103)


def _progress(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise CreativeReject("Invalid pilot action stage")
    return float(value)


def _stage(draw):
    if not isinstance(draw, ImageDraw.ImageDraw):
        raise CreativeReject("Expected a Pillow story-stage canvas")


def draw_power_disconnect(draw, attention):
    """Physical wall power lead: attached early, plug visibly separates first.

    This cue precedes the narrated city blackout; the radio continues glowing
    via the separately storyboarded receiver rather than being switched off.
    """
    _stage(draw)
    v = _progress(attention)
    travel = round(76 * v)
    # Socket is fixed to the wall/floor, cable and plug leave it continuously.
    draw.rounded_rectangle((580, 1046, 624, 1138), radius=8,
                           fill=(57, 76, 90), outline=(166, 180, 177), width=5)
    draw.ellipse((595, 1074, 610, 1090), fill=(17, 28, 41))
    draw.ellipse((595, 1102, 610, 1118), fill=(17, 28, 41))
    # A copper cable is mechanically attached to the radio body on the right.
    draw.line(((714, 1098), (699, 1132), (678-travel, 1150),
               (633-travel, 1099)), fill=(31, 38, 50), width=17, joint="curve")
    draw.line(((714, 1098), (699, 1132), (678-travel, 1150),
               (633-travel, 1099)), fill=COPPER, width=8, joint="curve")
    draw.rounded_rectangle((623-travel, 1086, 649-travel, 1110), radius=4,
                           fill=(152, 170, 174), outline=(30, 44, 56), width=3)
    for tip in (1092, 1103):
        draw.line(((620-travel, tip), (606-travel, tip)),
                  fill=LIGHT, width=4)
    return {"plug_separation_px": travel,
            "visual_semantics_verified": False}


def blackout_lit_window_count(event):
    """Five exterior lights go out one-by-one AFTER the unplug gesture."""
    v = _progress(event)
    return sum(1 for index in range(5) if v < (index + 1) / 5)


def draw_blackout_skyline(draw, event):
    """Show a real nighttime city through the observatory's exterior glass.

    Kept in the back wall, behind characters and the underground door. Existing
    abstract warning lamps are not substituted for the city's streetlights.
    """
    _stage(draw)
    v = _progress(event)
    # Wide panoramic sill, not words, signal icons, or a decorative waveform.
    draw.rounded_rectangle((486, 681, 931, 957), radius=15,
                           fill=NIGHT, outline=BUILDING_EDGE, width=9)
    draw.line(((500, 945), (916, 945)), fill=(191, 155, 110), width=6)
    for index in range(5):
        x = 505 + index * 81
        roof = 770 - (index % 3) * 32
        draw.rectangle((x, roof, x + 66, 941), fill=BUILDING,
                       outline=BUILDING_EDGE, width=3)
        lit = v < (index + 1) / 5
        for level in range(3):
            for col in range(2):
                px = x + 13 + col * 28
                py = roof + 23 + level * 43
                draw.rectangle((px, py, px + 13, py + 19),
                               fill=LIGHT if lit else DARK_WINDOW)
        # Individual streetlamps are larger, high-contrast outage witnesses.
        pole_x = x + 37
        draw.line(((pole_x, 941), (pole_x, 904)), fill=(123, 144, 154), width=5)
        draw.ellipse((pole_x-9, 892, pole_x+9, 910),
                     fill=LIGHT if lit else DARK_WINDOW)
    return {"lit_building_groups": blackout_lit_window_count(event),
            "visual_semantics_verified": False}


def draw_escape_stairs(draw):
    """Five perspective stair treads behind the escape door's hinged leaf.

    Called between the doorway cavity and door leaf drawing, so the closing
    door genuinely occludes the steps instead of drawing them ON the door.
    """
    _stage(draw)
    # Receding staircase beyond the threshold, pointing upward into a corridor.
    for index in range(5):
        shrink = index * 12
        y = 1095 - index * 92
        left = 736 + shrink
        right = 943 - shrink // 2
        draw.polygon(((left, y), (right, y),
                      (right-15, y+31), (left-12, y+31)),
                     fill=(79 + index*9, 96 + index*8, 113 + index*7),
                     outline=(188, 169, 133), width=4)
    return {"step_count": 5, "visual_semantics_verified": False}
