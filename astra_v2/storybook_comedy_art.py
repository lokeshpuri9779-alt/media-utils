"""Illustrated fox/rabbit character art for the isolated offline comedy pilot.

This deliberately does not alter ASTRA Main or the production character catalog.
Coordinates and shoulder anchors are defined in the native 1080x1920 canvas.
"""
import math
from PIL import Image, ImageDraw
from astra_v2.character_object_catalog import character

INK = (39, 43, 63, 255)
WHITE = (255, 249, 235, 255)


def metrics(index, t, x, y):
    bob = int(8 * math.sin(t * 2.8 + index * .013))
    return x, y + bob


def shoulder_anchor(index, t, x, y, side):
    x, y = metrics(index, t, x, y)
    y += int(7 * math.sin(t * 4.5))  # focused carry acting bounce
    return (x + side * 101, y + 123)


def palette(species):
    if species == "fox":
        return {"fur": (240, 120, 62, 255), "shade": (189, 75, 56, 255),
                "light": (255, 190, 113, 255), "muzzle": (255, 240, 209, 255),
                "outfit": (71, 156, 150, 255), "belly": (248, 216, 179, 255)}
    return {"fur": (241, 225, 207, 255), "shade": (198, 174, 170, 255),
            "light": (255, 245, 226, 255), "muzzle": (255, 248, 237, 255),
            "outfit": (149, 124, 192, 255), "belly": (255, 238, 218, 255)}


def _oval(draw, box, fill, outline=INK, width=7):
    draw.ellipse(tuple(int(v) for v in box), fill=fill, outline=outline, width=width)


def draw_storybook_character(image, index, t, x=540, y=1060,
                             expression="neutral", gesture="idle"):
    """Draw a layered, species-specific full-body cartoon.

    The carry_rig pose leaves the arms to the coordinated scene's joint solver.
    """
    species, role, style = character(index)
    if species not in ("fox", "rabbit"):
        raise ValueError("storybook actor must be fox or rabbit")
    if expression not in ("neutral", "happy", "focused", "surprised"):
        raise ValueError("unsupported storybook expression")
    if gesture not in ("idle", "point", "celebrate", "carry", "carry_rig"):
        raise ValueError("unsupported storybook gesture")
    p = palette(species)
    x, y = metrics(index, t, x, y)
    d = ImageDraw.Draw(image, "RGBA")
    sway = math.sin(t * 3.0 + index * .015)
    bounce = int((12 if expression == "surprised" else 7) * math.sin(t * 4.5))
    y += bounce

    # Tail behind the silhouette: the fox has a thick pale-tipped sweeping tail.
    if species == "fox":
        tail_shift = int(30 * math.sin(t * 2.7))
        d.polygon(((x + 82, y + 156), (x + 166, y + 165),
                   (x + 261 + tail_shift, y + 73), (x + 212 + tail_shift, y + 228),
                   (x + 121, y + 255)), fill=p["shade"])
        d.polygon(((x + 211 + tail_shift, y + 161), (x + 261 + tail_shift, y + 73),
                   (x + 231 + tail_shift, y + 187)), fill=p["muzzle"])
        d.line(((x + 83, y + 157), (x + 166, y + 165),
                (x + 261 + tail_shift, y + 73)), fill=INK, width=7, joint="curve")
    else:
        _oval(d, (x + 80, y + 195, x + 140, y + 251), WHITE, width=6)

    # Boots and articulated stepping legs.
    stride = int(20 * math.sin(t * 4.4))
    for side in (-1, 1):
        knee_x = x + side * (46 + int(9 * sway))
        foot_x = knee_x + side * (16 + stride)
        d.line(((x + side * 54, y + 226), (knee_x, y + 288),
                (foot_x, y + 351)), fill=INK, width=35, joint="curve")
        d.line(((x + side * 54, y + 225), (knee_x, y + 288),
                (foot_x, y + 338)), fill=p["shade"], width=24, joint="curve")
        _oval(d, (foot_x - 41, y + 329, foot_x + 41, y + 359),
              p["outfit"], width=5)

    # Jacket and collar with contrasting buttons; readable at phone resolution.
    _oval(d, (x - 119, y + 70, x + 119, y + 261), p["shade"], width=9)
    d.rounded_rectangle((x - 101, y + 100, x + 101, y + 240),
                        radius=35, fill=p["outfit"], outline=INK, width=8)
    d.polygon(((x - 73, y + 98), (x, y + 167), (x - 5, y + 104)),
              fill=p["muzzle"])
    d.polygon(((x + 73, y + 98), (x, y + 167), (x + 5, y + 104)),
              fill=p["muzzle"])
    for yy in (176, 205):
        _oval(d, (x - 7, y + yy - 7, x + 7, y + yy + 7),
              (248, 213, 113, 255), width=3)
    d.arc((x - 86, y + 176, x + 87, y + 238), 12, 172,
          fill=(255, 241, 227, 255), width=5)

    # Arms are omitted only for the coordinated full-body carry rig.
    if gesture != "carry_rig":
        for side in (-1, 1):
            shoulder = (x + side * 101, y + 123)
            if gesture == "point" and side == 1:
                hand = (x + 244, y + 26)
            elif gesture == "celebrate":
                hand = (x + side * 153, y - 109 + int(11 * sway))
            elif gesture == "carry":
                hand = (x + side * 70, y + 230)
            else:
                hand = (x + side * 160, y + 180 + int(15 * sway * side))
            mid = ((shoulder[0] + hand[0]) // 2 + side * 22,
                   (shoulder[1] + hand[1]) // 2)
            d.line((shoulder, mid, hand), fill=INK, width=31, joint="curve")
            d.line((shoulder, mid, hand), fill=p["fur"], width=23, joint="curve")
            _oval(d, (hand[0]-20, hand[1]-20, hand[0]+20, hand[1]+20),
                  p["light"], width=5)

    # Head drawn on its own layer for living eye and ear acting.
    head = Image.new("RGBA", image.size, (0, 0, 0, 0))
    h = ImageDraw.Draw(head, "RGBA")
    head_cy = y - 72
    ear_wiggle = int(8 * math.sin(t * 3.7))
    if species == "fox":
        for side in (-1, 1):
            h.polygon(((x + side * 83, head_cy - 105),
                       (x + side * (113 + ear_wiggle), head_cy - 261),
                       (x + side * 15, head_cy - 151)),
                      fill=p["fur"], outline=INK, width=7)
            h.polygon(((x + side * 76, head_cy - 141),
                       (x + side * 98, head_cy - 218),
                       (x + side * 43, head_cy - 158)),
                      fill=(251, 177, 162, 255))
        _oval(h, (x - 145, head_cy - 152, x + 145, head_cy + 109),
              p["fur"], width=9)
        for side in (-1, 1):
            _oval(h, (x + side * 74 - 53, head_cy + 17,
                      x + side * 74 + 53, head_cy + 101),
                  p["muzzle"], width=0)
    else:
        for side in (-1, 1):
            ear_tilt = int(13 * math.sin(t * 2.4 + side))
            h.ellipse((x + side * 90 - 41 + ear_tilt, head_cy - 313,
                       x + side * 90 + 41 + ear_tilt, head_cy - 87),
                      fill=p["fur"], outline=INK, width=8)
            h.ellipse((x + side * 90 - 19 + ear_tilt, head_cy - 279,
                       x + side * 90 + 19 + ear_tilt, head_cy - 113),
                      fill=(241, 172, 184, 255))
        _oval(h, (x - 130, head_cy - 142, x + 130, head_cy + 108),
              p["fur"], width=9)
        _oval(h, (x - 72, head_cy + 17, x + 72, head_cy + 103),
              p["muzzle"], width=0)

    # Large distinct expressive eyes, directional pupils, catchlights and brows.
    gaze = int(9 * math.sin(t * 1.1 + 1.0))
    for side in (-1, 1):
        eye_x = x + side * 61
        if expression == "happy":
            h.arc((eye_x - 32, head_cy - 60, eye_x + 32, head_cy - 8),
                  183, 355, fill=INK, width=8)
        else:
            _oval(h, (eye_x - 32, head_cy - 68, eye_x + 32,
                      head_cy + (17 if expression == "surprised" else 5)),
                  WHITE, width=5)
            pupil_r = 13 if expression == "surprised" else 16
            _oval(h, (eye_x + gaze - pupil_r, head_cy - 30 - pupil_r,
                      eye_x + gaze + pupil_r, head_cy - 30 + pupil_r),
                  INK, width=0)
            _oval(h, (eye_x + gaze - 4, head_cy - 42,
                      eye_x + gaze + 5, head_cy - 32),
                  WHITE, width=0)
        brow_y = head_cy - (96 if expression == "surprised" else 75)
        h.line(((eye_x - 26, brow_y + (11 if expression == "focused" else 0)),
                (eye_x + 25, brow_y - (11 if expression == "focused" else 0))),
               fill=INK, width=8)
    nose_color = (68, 49, 59, 255) if species == "fox" else (229, 143, 155, 255)
    _oval(h, (x-17, head_cy+40, x+17, head_cy+63), nose_color, width=3)
    if expression == "surprised":
        _oval(h, (x-13, head_cy+70, x+13, head_cy+99), INK, width=0)
    elif expression == "focused":
        h.line(((x - 22, head_cy + 89), (x + 23, head_cy + 89)),
               fill=INK, width=6)
    else:
        h.arc((x-33, head_cy+54, x+33, head_cy+100),
              5, 175, fill=INK, width=6)
    for side in (-1, 1):
        _oval(h, (x + side * 96 - 18, head_cy + 34,
                  x + side * 96 + 18, head_cy + 53),
              (249, 163, 139, 255), width=0)

    # Slight head tilt gives scenes a non-static acting pose.
    tilt = (3 if expression == "focused" else -4 if expression == "surprised"
            else 4 if expression == "happy" else 0) + int(2 * math.sin(t * 2))
    bbox = head.getbbox()
    if bbox:
        cut = head.crop((max(0, bbox[0]-35), max(0, bbox[1]-35),
                         min(image.width, bbox[2]+35), min(image.height, bbox[3]+35)))
        rotated = cut.rotate(tilt, resample=Image.Resampling.BICUBIC, expand=True)
        hx = int((bbox[0] + bbox[2]) / 2 - rotated.width / 2)
        hy = int((bbox[1] + bbox[3]) / 2 - rotated.height / 2)
        image.alpha_composite(rotated, (hx, hy))
    return species, role, style
