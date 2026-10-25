"""Foreground architectural depth without hiding verified background artwork.

ASTRA's prior opaque 920x680 observatory slab covered most of the original
verified scene art while asset checks still (correctly) confirmed a composite.
This module builds a physically legible room around an OPEN view: roof girders,
sidewalls, mullions, consoles and perspective floor. It never fabricates a
new background, downloads material, or changes publication authorization.

All drawing is local CPU Pillow vector work in the mid-screen subject region.
Characters, primary story objects, titles and captions are drawn separately.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_action_choreography import ACTION_SEQUENCE, action_state

STAGE_BOUNDS = (80, 555, 1000, 1260)
FRAME_SIZE = (1080, 1920)
INK = (16, 27, 44)
BEAM = (48, 62, 83)
BEAM_LIT = (110, 142, 160)
COPPER = (192, 154, 112)
FLOOR = (36, 49, 69)
FLOOR_HIGHLIGHT = (76, 96, 118)

DOOR_ACTIONS = frozenset({
    "hear_warning", "flee_door", "guard_knocking_door",
    "stop_stranger_switch", "survey_dead_city", "inspect_reverse_clock",
    "confront_mara_double", "face_duplicate_at_countdown",
    "split_glass_key", "seal_and_reveal_sea_door",
})
WARNING_ACTIONS = frozenset({
    "hear_warning", "flee_door", "guard_knocking_door", "survey_dead_city",
    "confront_mara_double", "face_duplicate_at_countdown", "split_glass_key",
})


def draw_actor_shadow(draw: ImageDraw.ImageDraw, x: int, y: int,
                      *, running=False, progress=0.0):
    """Place the actor on the physical floor; no blurred full-frame overlay."""
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(progress)):
        raise CreativeReject("Nonfinite character position/shadow time")
    width = 118 if not running else 145
    displacement = int(15 * progress) if running else 0
    cy = y+337
    draw.ellipse((x-width+displacement,cy-5,
                  x+width+displacement,cy+27),fill=(20,26,39))
    draw.arc((x-width+25,cy+5,x+width-25,cy+31),
             7,168,fill=(107,118,135),width=3)


def draw_observatory_stage(image: Image.Image, action: str, t: float,
                           duration: float):
    """Draw perspective set dressing AROUND the original scene-art window.

    Central window pixels (e.g. x=520,y=800) remain untouched. This is an
    intentional contract: the source image is visible and verifiable, unlike
    the previous large filled dark rectangle.
    """
    if image.mode != "RGB" or image.size != FRAME_SIZE:
        raise CreativeReject("Observatory stage expects RGB 1080x1920")
    if action not in ACTION_SEQUENCE:
        raise CreativeReject("Unknown authored set action: " + str(action))
    state = action_state(action,t,duration)
    d=ImageDraw.Draw(image)

    # Rear framing: chamfered lintel and wall planes retain most of the scene
    # image between x~180-900, y~645-1155. No central fill is painted.
    d.polygon(((80,555),(1000,555),(956,624),(125,624)),
              fill=BEAM,outline=BEAM_LIT,width=6)
    d.line(((142,607),(935,607)),fill=(177,172,152),width=5)
    d.polygon(((80,555),(145,627),(177,1160),(80,1240)),
              fill=BEAM,outline=BEAM_LIT,width=6)
    d.polygon(((1000,555),(938,627),(906,1160),(1000,1240)),
              fill=BEAM,outline=BEAM_LIT,width=6)
    d.line(((147,645),(177,1150)),fill=(146,172,179),width=4)
    d.line(((939,645),(906,1150)),fill=(146,172,179),width=4)

    # Tall glazed view: architecture overlays but does not replace background.
    d.arc((145,614,940,1260),183,358,fill=(115,145,169),width=11)
    d.arc((166,634,918,1231),184,357,fill=COPPER,width=3)
    for x in (426,710):
        d.line(((x,637),(x,1159)),fill=(57,83,105),width=13)
        d.line(((x+4,648),(x+4,1150)),fill=(161,170,158),width=3)
    d.line(((179,995),(906,995)),fill=(55,78,101),width=9)
    d.line(((184,999),(898,999)),fill=(167,175,165),width=2)

    # Mechanical room geometry: perspective floor, rails and tile vanishing
    # points; floor stays behind the actors' shoes and narrated foreground props.
    d.polygon(((177,1152),(910,1152),(999,1260),(80,1260)),
              fill=FLOOR,outline=FLOOR_HIGHLIGHT,width=5)
    for x in (130,280,430,570,710,860,980):
        d.line(((x,1256),(540+int((x-540)*.19),1159)),
               fill=(71,84,108),width=3)
    for row in (1190,1228):
        d.line(((114+(row-1150)*.39,row),
                (966-(row-1150)*.39,row)),fill=(78,87,108),width=3)
    d.line(((180,1151),(902,1151)),fill=(186,155,112),width=5)

    # Corner scientific instrumentation: crisp physical equipment without
    # dominating the narrative objects and repeated cartoon silhouettes.
    d.rounded_rectangle((105,855,163,1079),radius=9,
                        fill=(37,57,76),outline=(128,153,172),width=5)
    d.rounded_rectangle((939,854,981,1078),radius=8,
                        fill=(40,56,75),outline=(131,154,172),width=4)
    for base_x in (114,944):
        for i in range(3):
            y=887+i*58
            d.ellipse((base_x,y,base_x+21,y+21),
                      fill=(65,117,139) if i<2 else (177,138,91))
    # Concentric bolts and copper conduit give scene a foreground layer.
    for x in (106,969):
        for y in (658,791,1090):
            d.ellipse((x-5,y-5,x+5,y+5),fill=COPPER)
    d.arc((80,628,175,787),265,358,fill=(190,156,120),width=4)

    # Control lamps visibly respond to story context but never flash white.
    warning=action in WARNING_ACTIONS and (state.event>.18 or state.phase>=2)
    lamp=(241,160,91) if warning else (110,190,181)
    for i in range(7):
        x=260+i*91
        intensity = state.progress > (i/10) if warning else i%3 != 1
        d.ellipse((x-6,579,x+6,591),
                  fill=lamp if intensity else (60,75,91))

    # A second visible space beyond the room is preserved in the window.
    # The command is deliberately deterministic; neither PIL randomness nor
    # volatile state is used, enabling exact frame-to-frame reproducibility.
    return {
        "background_visible": True,
        "frame": STAGE_BOUNDS,
        "cue": state.cue,
        "warning_lamps": warning,
        "depth_layers": 4,
    }
