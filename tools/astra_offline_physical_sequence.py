"""Hand-authored repair mechanics for isolated 320x180 ASTRA CPU previews.

The colored-pixel witnesses prove only these fixed authored shapes survive
H.264; they cannot prove physical plausibility, semantic storytelling, or
release-quality animation. No model, assets, GPU, API, or publishing route.
"""
from __future__ import annotations
import math
from PIL import Image, ImageDraw

SIZE = (320, 180)
STAGES = ("setup", "attempt", "setback", "payoff")
CASES = ("glasshouse-sunshade", "footbridge-ducklings", "moon-mirror-garden")
# Distinct material colors, NOT semantic/character recognition.
HEMP = (244, 195, 112)
KNOT = (239, 219, 160)
HOOK = (196, 87, 42)
LASH = (246, 226, 163)
HANDLE = (246, 168, 90)
CLIP = (236, 235, 212)
STEEL = (104, 115, 137)

# (ROI, exact authored material color, tolerance, minimum late-frame pixels)
# Each ROI excludes captions and has no reliance on a headline label.
WITNESSES = {
    "glasshouse-sunshade": {
        "attempt": ("thin_cord_loops_pulley",
                    (92, 34, 118, 59), HEMP, 40, 23),
        "payoff": ("braided_rope_knotted_to_frame",
                   (273, 102, 310, 135), KNOT, 40, 32),
    },
    "footbridge-ducklings": {
        "setback": ("plank_retrieval_hook_visible",
                    (89, 114, 132, 145), HOOK, 26, 48),
        "payoff": ("reed_binding_at_both_bridge_posts",
                   (237, 83, 255, 116), LASH, 38, 26),
    },
    "moon-mirror-garden": {
        "attempt": ("brass_handle_rotates",
                    (251, 65, 264, 81), HANDLE, 38, 28),
        "payoff": ("replacement_metal_clip_locks_mirror",
                   (258, 59, 285, 94), CLIP, 38, 34),
    },
}


def _line(draw, points, color, width=3):
    draw.line(points, fill=(*color, 255), width=width, joint="curve")


def render_physical_sequence(case_id, stage, progress):
    """Layer genuine authored repair marks at the hand/prop contact points."""
    if case_id not in CASES or type(stage) is not int or stage not in range(4):
        raise ValueError("Unknown isolated physical-action profile")
    if (type(progress) not in (int, float) or not math.isfinite(progress)
            or not 0.0 <= progress <= 1.0):
        raise ValueError("Invalid physical-action progress")
    t = float(progress)
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    if case_id == "glasshouse-sunshade":
        if stage == 1:
            # Cord winds visibly around the overhead pulley, then tracks the
            # advancing canvas. A bare contact line cannot satisfy this cue.
            if t > 0.18:
                d.arc((94, 35, 115, 56), 20, 320,
                      fill=(*HEMP, 255), width=3)
                d.arc((98, 39, 111, 52), 0, 300,
                      fill=(*HEMP, 255), width=2)
                _line(d, [(104, 56), (97, 70),
                          (90 + round(26*t), 88)], HEMP, 3)
        elif stage == 2:
            # Torn thin cord recoils from its attachment.
            _line(d, [(104, 51), (105-round(10*t), 66),
                      (95-round(8*t), 75)], (162, 105, 58), 2)
        elif stage == 3 and t > 0.4:
            # A braided replacement rope is tensioned across the canvas and
            # tied around the fixed outer frame, not merely touching it.
            _line(d, [(48+round(231*t), 75), (290, 112),
                      (293, 124)], KNOT, 4)
            _line(d, [(287, 113), (300, 117), (290, 124),
                      (303, 130)], KNOT, 3)
            d.ellipse((286, 116, 299, 129),
                      outline=(*KNOT, 255), width=3)
            _line(d, [(296, 123), (308, 133)], HEMP, 2)

    elif case_id == "footbridge-ducklings":
        if stage == 1:
            # A stone holds the *near* plank end before the flood tears it up.
            d.ellipse((118, 96, 140, 108),
                      fill=(174, 160, 126, 255), outline=(*STEEL, 255), width=2)
        elif stage == 2:
            # The securing stone is lifted by floodwater; a retrieval hook
            # reaches the dislodged plank from the beaver's foreground paw.
            stone_x = 135 + round(24*t)
            stone_y = 102 + round(24*t)
            d.ellipse((stone_x-9, stone_y-5, stone_x+9, stone_y+6),
                      fill=(174, 160, 126, 255),
                      outline=(*STEEL, 255), width=2)
            if t > 0.12:
                hook_x = 111 + round(12*t)
                hook_y = 118 + round(16*t)
                _line(d, [(68, 119), (85, 116+round(8*t)),
                          (hook_x, hook_y)], HOOK, 4)
                d.arc((hook_x-6, hook_y-4, hook_x+6, hook_y+9),
                      20, 210, fill=(*HOOK, 255), width=3)
        elif stage == 3:
            # Two *separate* bindings wrap around both bridge posts. The
            # right-hand lashing is completed only late in the payoff.
            if t > 0.2:
                _line(d, [(76, 97), (88, 104), (77, 111),
                          (88, 101), (77, 94)], LASH, 3)
                _line(d, [(83, 108), (109, 110)], LASH, 3)
            if t > 0.6:
                _line(d, [(111, 110), (240, 110)], LASH, 3)
                _line(d, [(240, 96), (252, 104), (240, 112),
                          (251, 100), (240, 92)], LASH, 3)
                d.ellipse((238, 99, 252, 110),
                          outline=(*LASH, 255), width=2)

    elif case_id == "moon-mirror-garden":
        if stage == 1:
            # Brass lever actually sweeps through a bounded arc around the
            # mounting pivot, rather than a static colored contact trace.
            d.ellipse((255, 77, 263, 85), fill=(*STEEL, 255))
            end_x = 241 + round(13*t)
            end_y = 98 - round(25*t)
            _line(d, [(259, 82), (end_x, end_y)], HANDLE, 5)
            d.ellipse((end_x-4, end_y-4, end_x+4, end_y+4),
                      fill=(*HANDLE, 255))
        elif stage == 2:
            # Bent original pin falls away before the replacement is fitted.
            drop = round(28*t)
            _line(d, [(268, 71+drop), (277, 74+drop),
                      (273, 80+drop)], (215, 126, 111), 3)
        elif stage == 3:
            # Hand introduces one U-shaped metal clip and *closes* it around
            # the bracket. The original broken pin is no longer in the socket.
            clip_x = 241 + round(22*min(1.0, t/.78))
            clip_y = 89 - round(12*min(1.0, t/.78))
            _line(d, [(clip_x, clip_y), (clip_x, clip_y-12),
                      (clip_x+11, clip_y-12), (clip_x+11, clip_y)], CLIP, 4)
            if t > 0.72:
                _line(d, [(262, 77), (274, 77)], CLIP, 4)
                _line(d, [(264, 68), (277, 78)], CLIP, 3)
                d.ellipse((265, 70, 274, 80),
                          outline=(*CLIP, 255), width=2)
    return layer


def _matching_pixels(image, box, color, tolerance):
    if not isinstance(image, Image.Image) or image.mode != "RGB" or image.size != SIZE:
        raise ValueError("Expected decoded 320x180 RGB MP4 frame")
    x0, y0, x1, y1 = box
    if not 0 <= x0 < x1 <= SIZE[0] or not 28 <= y0 < y1 <= 160:
        raise ValueError("Physical-action witness overlaps caption or leaves scene")
    return sum(1 for pixel in image.crop(box).getdata()
               if all(abs(pixel[k]-color[k]) <= tolerance for k in range(3)))


def audit_physical_sequence(case_id, stage, early, late):
    """Encoded-frame material witnesses, deliberately not semantic approval."""
    if (case_id not in WITNESSES or type(stage) is not int or stage not in range(4)
            or STAGES[stage] not in WITNESSES[case_id]):
        raise ValueError("Unknown or unsupported authored repair moment")
    label, region, color, tolerance, minimum = WITNESSES[case_id][STAGES[stage]]
    before = _matching_pixels(early, region, color, tolerance)
    after = _matching_pixels(late, region, color, tolerance)
    # Check encoded material survival, not just generic scene movement.
    passed = after >= minimum and after > before + 5
    return {
        "case_id": case_id, "stage": STAGES[stage], "witness": label,
        "earlier_matching_pixels": before, "later_matching_pixels": after,
        "min_later_pixels": minimum, "passed": passed,
        "semantics": "not_verified", "hand_prop_mechanics": "not_verified",
        "manual_review_required": True,
        "approved": False, "production_ready": False, "published": False,
    }
