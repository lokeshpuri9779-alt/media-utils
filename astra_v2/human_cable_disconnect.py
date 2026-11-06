"""Original, review-only Episode 1 radio-cable disconnection staging.

This depicts an authored disconnect before the previously implemented city
blackout. It does not infer an unseen action, evaluate semantic quality, or
authorize publication. No provider or alternate renderer is used.
"""
from __future__ import annotations

import math
from PIL import ImageDraw
from astra_errors import CreativeReject

RADIO_PORT = (530, 1070)
CABLE_ANCHOR = (415, 1174)
COPPER = (208, 150, 85)
BRIGHT = (250, 213, 134)
SHEATH = (18, 35, 48)


def _smooth(progress):
    v = max(0., min(1., progress))
    return v * v * (3 - 2 * v)


def unplug_pose(progress):
    """Fixed plug and socket geometry from the Episode 1 story clock.

    The cable detaches fully by progress=.44, BEFORE the city blackout
    begins at progress>.46. A moving character wrist can grip exactly the
    same connector location. Values are source-frame pixels before crop.
    """
    if type(progress) not in (int, float) or not math.isfinite(progress) or not 0 <= progress <= 1:
        raise CreativeReject("Invalid narrated cable-disconnect time")
    fraction = _smooth((progress - .22) / .22)
    grip = (round(509 - 70 * fraction), round(1070 - 29 * fraction))
    tip = (grip[0] + 21, grip[1])
    return {
        "grip": grip,
        "plug_tip": tip,
        "port": RADIO_PORT,
        "disconnection_fraction": fraction,
        "fully_disconnected": fraction >= 1,
        "narrated_action_visible": "not_verified",
    }


def draw_radio_cable_disconnect(draw, progress):
    """Place a real socket, a gripped connector, and its trailing lead.

    A physical plug starts inside the radio input; the visible separation
    happens before the existing streetlights-darken event. Reuse the actual
    2D actor wrist to show contact, not a disembodied pointer.
    """
    if not isinstance(draw, ImageDraw.ImageDraw):
        raise CreativeReject("Cable disconnection requires real Pillow surface")
    pose = unplug_pose(progress)
    gx, gy = pose["grip"]
    px, py = RADIO_PORT
    # Cable trailing from the connector, NOT a decorative beam toward radio.
    path = ((gx-25, gy+5), (449, 1113), CABLE_ANCHOR)
    draw.line(path, fill=SHEATH, width=18, joint="curve")
    draw.line(path, fill=COPPER, width=8, joint="curve")
    # Original portable receiver sits at (620,1050) with left edge x=530.
    # This input remains stationary, leaving an unmistakable gap after pull.
    draw.ellipse((px-12,py-15,px+12,py+15), fill=(69,91,111),
                 outline=(232,183,109),width=4)
    draw.ellipse((px-6,py-9,px+6,py+9),fill=(13,27,40))
    # The end of the lead travels with Mara's hand.
    draw.rounded_rectangle((gx-19,gy-12,gx+21,gy+12),radius=6,
                           fill=(65,83,99),outline=BRIGHT,width=4)
    draw.rounded_rectangle((gx+14,gy-7,gx+28,gy+7),radius=3,
                           fill=(183,192,192),outline=(52,75,91),width=2)
    return pose


def draw_wrist_grip_on_plug(draw, wrist, pose):
    """Overlay gripping fingers only at the actual solved right-wrist point."""
    if (not isinstance(draw, ImageDraw.ImageDraw) or not isinstance(pose,dict)
            or not isinstance(wrist,(tuple,list)) or len(wrist)!=2
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in wrist)
            or tuple(wrist) != pose.get("grip")):
        raise CreativeReject("Detached plug is not bound to actual actor wrist")
    x,y=map(round,wrist)
    # The sleeve/wrist is painted by Mara's rig; these top-layer skin arcs
    # make contact readable without hiding the metal connector entirely.
    draw.arc((x-18,y-14,x+16,y+16),25,145,fill=(240,185,146),width=7)
    draw.arc((x-18,y-14,x+16,y+16),220,324,fill=(240,185,146),width=7)
    return {"wrist":(x,y),"plug_gripped":True,
            "narrated_action_visible":"not_verified"}
