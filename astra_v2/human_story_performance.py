"""Story-specific CPU-animated human actor for The Tomorrow Signal pilot.

This is a bounded, original 2D character performance, not generic clipart,
real-person imagery, neural video, or proof of general-purpose human animation.
Unknown actors/actions are rejected rather than falling back to a signal icon.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

from astra_errors import CreativeReject

PILOT_ID = "rayvan-season-01-episode-01"
ACTIONS = (
    "discover_radio",
    "trace_cable",
    "hear_warning",
    "flee_door",
)
INK = (24, 34, 49)
SKIN = (198, 142, 111)
HAIR = (42, 37, 51)
JACKET = (51, 121, 139)
PANTS = (42, 55, 79)
RADIO = (62, 73, 93)
GOLD = (249, 190, 92)


def validate_human_scene(shot):
    """Only authored pilot beats can use this exact four-action character grammar."""
    if shot.get("story_visual_seed") != PILOT_ID:
        raise CreativeReject("Human performer not approved for this story identity")
    if shot.get("story_human_actor") != "mara":
        raise CreativeReject("Unknown human actor; no procedural fallback")
    action = shot.get("story_human_action")
    if action not in ACTIONS:
        raise CreativeReject("Unrenderable human action: " + str(action))
    if shot.get("story_cast"):
        raise CreativeReject("Human pilot does not support an animal cast")
    narration = str(shot.get("speech") or "").lower()
    if not narration.strip():
        raise CreativeReject("Missing narrated human action")
    if action in ("discover_radio", "trace_cable") and "radio" not in narration:
        raise CreativeReject("Radio action lacks a narrated radio")
    if action == "hear_warning" and not any(word in narration for word in ("voice", "countdown", "blackout")):
        raise CreativeReject("Warning scene lacks a narrated warning")
    if action == "flee_door" and not any(word in narration for word in ("door", "stairs")):
        raise CreativeReject("Escape scene has no door or stairs")
    visual = str(shot.get("visual") or "").lower()
    expected = "signal" if action in ("discover_radio", "trace_cable") else "door"
    if visual != expected:
        raise CreativeReject("Pilot action requires authored " + expected + " scene")
    return "human"


def _line(draw, coordinates, color=INK, width=12):
    draw.line(coordinates, fill=color, width=width, joint="curve")


def _radio(draw, x, y, t, *, glow=True, portable=False):
    """Handmade radio with moving frequency pulse and distinct readable antenna."""
    w, h = (180, 135) if portable else (225, 180)
    draw.rounded_rectangle((x-w//2, y-h//2, x+w//2, y+h//2),
                           radius=19, fill=RADIO, outline=(167, 180, 195), width=7)
    draw.rounded_rectangle((x-w//2+20, y-h//2+25, x+w//2-20, y+17),
                           radius=10, fill=(13, 26, 45), outline=(91, 145, 171), width=4)
    for k in range(8):
        xx=x-w//2+28+k*(w-55)//7
        height=int(8+23*(.5+.5*math.sin(t*7+k*.95)))
        _line(draw, ((xx,y+6-height//2),(xx,y+6+height//2)),
              (120, 219, 226) if glow else (93, 132, 155), 4)
    draw.ellipse((x+w//2-48, y+h//2-44, x+w//2-22, y+h//2-18),
                 fill=GOLD if glow and int(t*4)%2==0 else (110, 107, 97))
    _line(draw, ((x-w//2+45,y-h//2),(x-w//2+2,y-h//2-62)), (178, 197, 205), 7)
    return (x-w//2, y-h//2, x+w//2, y+h//2)


def _door(draw, open_amount):
    """A physical door changing its opening, not a decorative portal glyph."""
    draw.polygon(((660,606),(947,606),(1007,1200),(619,1200)),
                 fill=(23, 32, 49), outline=(197, 156, 118), width=15)
    draw.polygon(((697,640),(920,638),(950,1155),(655,1155)),
                 fill=(13, 17, 35))
    travel=int(160*open_amount)
    draw.polygon(((682,655),(902-travel,680),(916-travel,1127),(672,1150)),
                 fill=(95, 72, 98), outline=(211, 187, 166), width=9)
    draw.ellipse((853-travel,895,872-travel,916), fill=GOLD)
    # Escape glow stays within the stage, separate from title/captions.
    for k in range(3):
        xx=920+k*20
        _line(draw, ((xx,695),(xx,1115)), (70+k*25, 112+k*19, 157+k*14), 5)


def _mara(draw, x, y, t, *, reaching=False, alarm=False, running=False, carrying=False):
    """Persistent cel-shaded silhouette with articulated arms/legs and expression."""
    bounce=int(6*math.sin(t*2.8))
    if running:
        bounce=int(15*math.sin(t*11))
    y+=bounce
    limb=int(28*math.sin(t*10)) if running else int(7*math.sin(t*2))
    # Legs and shoes behind the body.
    _line(draw, ((x-37,y+200),(x-55-limb,y+340)), PANTS, 39)
    _line(draw, ((x+39,y+200),(x+56+limb,y+340)), PANTS, 39)
    _line(draw, ((x-56-limb,y+339),(x-106-limb,y+339)), INK, 28)
    _line(draw, ((x+56+limb,y+339),(x+106+limb,y+339)), INK, 28)
    # Back ponytail behind head makes Mara recognisable across shots.
    draw.ellipse((x-113,y-220,x-39,y-85),fill=HAIR)
    draw.ellipse((x-87,y-282,x+91,y-71),fill=HAIR,outline=INK,width=8)
    draw.ellipse((x-66,y-253,x+70,y-94),fill=SKIN,outline=INK,width=6)
    draw.polygon(((x-75,y-251),(x-11,y-279),(x+89,y-218),(x+57,y-248),
                  (x+19,y-228),(x-72,y-208)), fill=HAIR)
    # Eyes and animated blink; eyebrows convey alarm at the warning.
    blink=abs(math.sin(t*1.55))>.991
    for dx in (-28,30):
        eye_y=y-170
        if blink:
            _line(draw,((x+dx-10,eye_y),(x+dx+10,eye_y)), INK, 4)
        else:
            draw.ellipse((x+dx-9,eye_y-10,x+dx+9,eye_y+9),fill=(247,247,242))
            draw.ellipse((x+dx-3,eye_y-7,x+dx+5,eye_y+7),fill=INK)
        offset=-13 if alarm else -22
        _line(draw,((x+dx-12,eye_y+offset),(x+dx+11,eye_y+offset+(4 if alarm else 0))),HAIR,5)
    if alarm:
        draw.ellipse((x-11,y-122,x+11,y-92),fill=(74,40,53))
    else:
        draw.arc((x-26,y-135,x+29,y-105),0,175,fill=(111,62,70),width=5)
    draw.polygon(((x-51,y-80),(x+49,y-80),(x+86,y+210),(x-91,y+210)),
                 fill=JACKET,outline=INK,width=8)
    draw.polygon(((x-23,y-76),(x+23,y-76),(x+11,y+180),(x-14,y+180)),
                 fill=(215, 224, 216))
    draw.line(((x,y-64),(x,y+188)),fill=(20,65,85),width=6)
    draw.ellipse((x-8,y+125,x+8,y+141),fill=GOLD)
    # Two separately posed arms, with a clear target-reaching gesture.
    left_hand=(x-124,y+128)
    right_hand=(x+145,y-38) if reaching else ((x+144,y+10) if carrying else (x+113+limb,y+155))
    if running:
        left_hand=(x-149,y+50-limb)
        right_hand=(x+133,y+55+limb)
    _line(draw, ((x-58,y-40),left_hand), JACKET, 35)
    _line(draw, ((x+54,y-40),right_hand), JACKET, 35)
    for hx,hy in (left_hand,right_hand):
        draw.ellipse((hx-17,hy-17,hx+17,hy+17),fill=SKIN,outline=INK,width=3)


def draw_human_scene(image, shot, t):
    """Draw only authenticated pilot action geometry in the 1080x1920 scene stage."""
    validate_human_scene(shot)
    if image.mode != "RGB" or image.size != (1080, 1920):
        raise CreativeReject("Human episode requires RGB 1080x1920 Studio frame")
    action=shot["story_human_action"]
    d=ImageDraw.Draw(image)
    # Stage framing and a persistent observatory silhouette.
    d.rounded_rectangle((80,555,1000,1235),radius=28,
                        fill=(27,43,64),outline=(88,108,127),width=7)
    d.ellipse((545,620,930,1005),fill=(36,62,87),outline=(145,160,166),width=12)
    d.ellipse((620,685,850,916),outline=(177,167,143),width=7)
    for xx in (145,245,345):
        d.rectangle((xx,1060,xx+19,1210),fill=(73,93,109))
    d.polygon(((83,1190),(1000,1190),(1000,1260),(83,1260)),
              fill=(58,64,80))
    if action == "discover_radio":
        _radio(d,750,995,t,glow=True)
        _line(d,((750,1080),(750,1195)),(134,112,84),16)
        _mara(d,365+int(18*math.sin(t*.5)),885,t,reaching=True)
    elif action == "trace_cable":
        _radio(d,757,945,t)
        # Distinct floor cable connecting radios, read as a traceable object.
        _line(d,((751,1039),(718,1158),(540,1185),(373,1108)),GOLD,10)
        _radio(d,342,1109,t,glow=False,portable=True)
        _mara(d,605,873,t,reaching=True)
    elif action == "hear_warning":
        _door(d,0.32+0.08*math.sin(t))
        _radio(d,748,1065,t,glow=True,portable=True)
        # City blackout as an on-screen event, not a static caption.
        for j in range(5):
            cx=688+j*57
            d.rectangle((cx,710,cx+31,812), fill=(27,36,57))
            if t<1.2+(j*.22):
                d.rectangle((cx+7,736,cx+21,755),fill=GOLD)
        _mara(d,350,872,t,reaching=True,alarm=True)
    elif action == "flee_door":
        openness=max(.08,.76-min(1,t/5)*.63)
        _door(d,openness)
        _mara(d,420-int(min(140,t*29)),881,t,running=True,carrying=True,alarm=True)
        # The radio is visibly carried while Mara runs.
        _radio(d,525-int(min(140,t*29)),979+int(13*math.sin(t*11)),t,portable=True)
    else:
        raise CreativeReject("Unknown human action")
    return True
