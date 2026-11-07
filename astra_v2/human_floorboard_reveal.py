"""An original CPU 2D floor-hatch reveal for the reviewed Mara pilot.

Only the Episode 1 'trace_cable' scene uses this stage geometry. It is not a
general scene generator, and even a successful render cannot establish video
semantic fidelity without an independent complete-MP4 review.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw
from astra_errors import CreativeReject


# The boarded trapdoor sits beside the visible cable end and the authored
# second radio (center 342, 1109). Keep all geometry in the middle scene stage.
OPENING = ((238, 1078), (468, 1078), (500, 1190), (217, 1190))
# Rotate around the FAR edge of the cavity. The original leftward-open
# panel left the camera crop in the decoded MP4 despite passing pixel tests.
# Raising the near edge toward the back of the set leaves a visibly upright
# wooden hatch IN the approved Stage close-up, behind the delayed second radio.
LIFTED_BOARD = ((238, 1078), (468, 1078), (468, 840), (238, 840))
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

# Source radio socket -> visible cable across the floor -> concealed hatch.
# Both endpoints are in the same coordinate space as the original Episode 1
# draw_human_scene. The second (under-floor) segment stays hidden until the
# hatch opens; the second receiver itself is handled by the performance layer.
EXPOSED_CABLE = ((750, 1038), (713, 1092), (654, 1141),
                 (548, 1182), (471, 1168))
CONCEALED_CABLE = ((471, 1168), (414, 1130), (358, 1110))


def _cable_progress_point(path, fraction):
    """Interpolate along the polyline by physical length, not vertex count."""
    if type(fraction) not in (int, float) or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise CreativeReject("Invalid floor-cable trace progress")
    lengths = [math.dist(a, b) for a, b in zip(path, path[1:])]
    remaining = fraction * sum(lengths)
    for index, length in enumerate(lengths):
        if remaining <= length:
            q = remaining / length if length else 0.
            a, b = path[index:index + 2]
            return (round(a[0] + q * (b[0] - a[0])),
                    round(a[1] + q * (b[1] - a[1])))
        remaining -= length
    return path[-1]


def draw_floor_cable_trace(draw, attention, event):
    """Animate following a visible physical cable into the floorboard hatch.

    A moving trace spot conveys inspection; it is NOT evidence that Mara's hand
    physically followed the wire in the encoded MP4. This remains review-only.
    """
    if (not isinstance(draw, ImageDraw.ImageDraw)
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or not 0 <= v <= 1 for v in (attention, event))):
        raise CreativeReject("Invalid authored floor-cable trace")
    # The wire has an actual dark sheath and copper core, not just a short gold
    # overlay that can be mistaken for floor decoration at the Studio zoom.
    draw.line(EXPOSED_CABLE, fill=(10, 27, 40), width=20, joint="curve")
    draw.line(EXPOSED_CABLE, fill=(205, 144, 73), width=10, joint="curve")
    # Grounded socket at the original radio's lower edge.
    sx, sy = EXPOSED_CABLE[0]
    draw.rounded_rectangle((sx - 14, sy - 11, sx + 14, sy + 11), radius=5,
                           fill=(56, 75, 91), outline=(248, 200, 131), width=3)

    # Follow the wire continuously rather than switching on several segments
    # instantaneously at the floorboard discovery moment.
    marker = _cable_progress_point(EXPOSED_CABLE, attention)
    # Use the exact travelled distance to light only the visited wire section.
    total = sum(math.dist(a, b) for a, b in zip(EXPOSED_CABLE, EXPOSED_CABLE[1:]))
    target = attention * total
    lit = [EXPOSED_CABLE[0]]
    for a, b in zip(EXPOSED_CABLE, EXPOSED_CABLE[1:]):
        seg = math.dist(a, b)
        if target >= seg:
            lit.append(b)
            target -= seg
        else:
            if target > 0:
                q = target / seg
                lit.append((round(a[0] + q * (b[0] - a[0])),
                            round(a[1] + q * (b[1] - a[1]))))
            break
    if len(lit) > 1:
        draw.line(lit, fill=(246, 206, 110), width=7, joint="curve")
    mx, my = marker
    draw.ellipse((mx - 13, my - 13, mx + 13, my + 13),
                 fill=(249, 230, 156), outline=(71, 104, 111), width=4)

    # The continuation into the hidden floor space is disclosed ONLY after
    # the existing hatch event has progressed and the second radio can appear.
    revealed = event >= .25
    if revealed:
        draw.line(CONCEALED_CABLE, fill=(13, 31, 45), width=18, joint="curve")
        draw.line(CONCEALED_CABLE, fill=(249, 190, 92), width=9, joint="curve")
    return {"marker": marker, "underfloor_connection_visible": revealed,
            "visual_semantics_verified": False}


# Capture only the small below-floor space while adding the second receiver.
# Restoring the original pixels, then masking the hatch opening, prevents the
# radio's antenna and case from floating over the raised panel. The same
# existing _radio call is used; no new asset/engine is introduced.
HIDDEN_RADIO_CAPTURE = (210, 960, 515, 1210)


def draw_radio_inside_hatch(image, draw, event, radio_draw, t):
    """Clip Episode 1's second radio behind its *moving* floorboard panel.

    Source-frame CPU 2D occlusion, not a claim that a reviewer can identify
    an underground room in the resulting full encoded video.
    """
    fraction = floorboard_reveal_fraction(event)
    if (not isinstance(image, Image.Image) or image.mode != "RGB"
            or image.size != (1080, 1920)
            or not isinstance(draw, ImageDraw.ImageDraw)
            or not callable(radio_draw)
            or type(t) not in (int, float) or not math.isfinite(t)
            or t < 0):
        raise CreativeReject("Invalid reviewed hidden-radio drawing surface")
    l, top, r, bottom = HIDDEN_RADIO_CAPTURE
    before = image.crop((l, top, r, bottom))
    # The existing receiver, original proportions and original radio timing.
    radio_draw(draw, 342, 1109, t, glow=False, portable=True)
    painted = image.crop((l, top, r, bottom))
    image.paste(before, (l, top))

    mask = Image.new("L", (r-l, bottom-top), 0)
    masker = ImageDraw.Draw(mask)
    masker.polygon([(x-l, y-top) for x, y in OPENING], fill=255)
    # The hinged panel is a *foreground occluder*, including while half
    # lifted: no instant pop in front of a still-closed floorboard.
    masker.polygon([(x-l, y-top) for x, y in floorboard_panel(event)],
                   fill=0)
    image.paste(painted, (l, top), mask)
    return {"hatch_open_fraction": fraction,
            "masked_behind_moving_panel": True,
            "semantic_quality": "not_verified",
            "publication_approval": False}
