"""Original CPU-only staircase art for Episode 1's authored escape.

The staircase is drawn BEHIND the closing hinged door so viewers can follow
Mara's destination, not mistaken for light strips on top of the door. This
does not constitute independent semantic approval of the encoded video.
"""
from __future__ import annotations

import math
from PIL import ImageDraw
from astra_errors import CreativeReject

# The existing doorway is at ~x660..950 and the camera's late crop ends near
# x901. Keep the important treads inside both the door opening and that crop.
STAIR_TREADS = tuple(
    (756 + i * 17, 1117 - i * 76, 899 - i * 8)
    for i in range(5)
)

def escape_door_open_fraction(progress):
    """Keep stairs exposed during escape; swing the heavy door shut near end."""
    if type(progress) not in (int, float) or not math.isfinite(progress) or not 0 <= progress <= 1:
        raise CreativeReject("Invalid authored staircase escape progress")
    t=max(0., min(1., (progress-.66)/.30))
    eased=t*t*(3.-2.*t)
    return .76*(1.-eased)

def draw_staircase_beyond_door(draw):
    """Five narrowing perspective treads through the observatory doorway."""
    if not isinstance(draw, ImageDraw.ImageDraw):
        raise CreativeReject("Staircase needs Pillow stage canvas")
    # Visible angled banister and landing distinguish a stairwell from
    # generic alternating bars or a wall of illuminated rectangles.
    draw.polygon(((740,1149),(905,1149),(881,778),(812,778)),
                 fill=(22,35,53))
    draw.line(((746,1141),(807,803)),fill=(170,157,137),width=7)
    draw.line(((895,1141),(866,803)),fill=(170,157,137),width=7)
    for i,(x,y,right) in enumerate(STAIR_TREADS):
        draw.polygon(((x,y),(right,y),(right-12,y+25),(x-11,y+25)),
                     fill=(77+i*9,94+i*8,111+i*7),
                     outline=(194,171,132),width=4)
        draw.line(((x-10,y+23),(right-12,y+23)),
                  fill=(35,52,73),width=5)
    return {"step_count":len(STAIR_TREADS),
            "behind_hinged_door":True,
            "semantic_quality":"not_verified",
            "publication_approval":False}
