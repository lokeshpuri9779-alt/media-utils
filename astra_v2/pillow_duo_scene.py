"""CPU-only two-character Pillow staging for explicitly named fiction pairs.

No random stock characters: only activate when BOTH supported actors occur in
the same shot's narration or visual prompt. Keep within Studio subject region.
"""
import math
import re
from PIL import ImageDraw

ACTORS = ("fox", "rabbit", "cat", "dog", "owl", "mouse", "otter", "squirrel")
COLORS = {"fox": (235, 119, 54), "rabbit": (235, 217, 193),
          "cat": (203, 142, 91), "dog": (180, 130, 83),
          "owl": (159, 117, 84), "mouse": (178, 171, 175),
          "otter": (151, 107, 77), "squirrel": (193, 123, 72)}
ALIASES = {"rabbit": r"\\b(?:rabbit|bunny|hare)\\b",
           "dog": r"\\b(?:dog|puppy)\\b",
           "cat": r"\\b(?:cat|kitten)\\b",
           "mouse": r"\\b(?:mouse|mice)\\b"}

def scene_pair(shot):
    narration = " ".join(str(shot.get(k) or "") for k in
                         ("speech", "visual_prompt", "action")).lower()
    found = []
    for name in ACTORS:
        pattern = ALIASES.get(name, r"\\b" + name + r"\\b")
        match = re.search(pattern, narration)
        if match:
            found.append((match.start(), name))
    found.sort()
    return tuple(name for _, name in found[:2]) if len(found) >= 2 else ()

def draw_duo(image, shot, t):
    pair = scene_pair(shot)
    if not pair:
        return False
    d = ImageDraw.Draw(image)
    action = str(shot.get("story_action") or "idle").lower()
    for i, name in enumerate(pair):
        x = 305 + i * 470
        phase = t * (8 if action == "run" else 4) + i * math.pi
        stride = int(28 * math.sin(phase)) if action in ("run", "walk") else 0
        hop = int(50 * abs(math.sin(t * 4))) if action == "jump" else 0
        y = 885 - hop + int(7 * math.sin(t * 2 + i))
        color = COLORS[name]
        dark = (33, 38, 52)
        d.ellipse((x-115, 1210, x+115, 1233), fill=(19, 33, 47))
        for side in (-1, 1):
            sx = x + side * 56
            leg = stride * side
            d.line((sx, y+170, sx+leg, y+315-abs(leg)//3),
                   fill=color, width=37)
            d.ellipse((sx+leg-28, y+298-abs(leg)//3,
                       sx+leg+28, y+323-abs(leg)//3), fill=(76, 173, 175) if i == 0 else (162, 127, 193))
        d.rounded_rectangle((x-95, y+40, x+95, y+225), radius=55,
                            fill=(57, 156, 157) if i == 0 else (140, 115, 180))
        reach = int(65 * math.sin(t*5)) if action in ("wave", "repair", "carry", "pick", "throw") else 0
        for side in (-1, 1):
            sx=x+side*90
            d.line((sx,y+80,sx+side*65,y+140-abs(reach) if side==1 else y+145),
                   fill=color,width=25)
            if side == 1 and reach:
                d.ellipse((sx+side*65-15,y+125-abs(reach),sx+side*65+15,y+155-abs(reach)),fill=color)
        d.ellipse((x-116,y-175,x+116,y+63),fill=color,outline=(250,224,193),width=5)
        if name in ("fox", "cat", "rabbit", "mouse", "squirrel"):
            for side in (-1, 1):
                if name == "rabbit":
                    d.ellipse((x+side*68-27,y-315,x+side*68+27,y-125),fill=color)
                    d.ellipse((x+side*68-12,y-290,x+side*68+12,y-145),fill=(240,170,179))
                else:
                    d.polygon(((x+side*50,y-120),(x+side*104,y-245),
                               (x+side*113,y-75)),fill=color)
        blink = abs(math.sin(t*1.7+i)) > .985
        for side in (-1, 1):
            ex=x+side*48
            if blink:
                d.line((ex-17,y-54,ex+17,y-54),fill=dark,width=6)
            else:
                d.ellipse((ex-15,y-69,ex+15,y-27),fill=(255,255,255))
                d.ellipse((ex-6,y-56,ex+7,y-33),fill=dark)
        d.ellipse((x-12,y-8,x+12,y+10),fill=dark)
        if action in ("hide", "look"):
            d.arc((x-27,y+5,x+27,y+40),0,180,fill=dark,width=5)
        else:
            d.ellipse((x-10,y+22,x+10,y+47),fill=dark)
    if re.search(r"\\b(?:box|parcel|package|gift)\\b",
                 " ".join(str(shot.get(k) or "") for k in ("speech","visual_prompt","action")).lower()):
        d.rounded_rectangle((485,1140,595,1250),radius=8,fill=(157,109,65))
        d.line((540,1140,540,1250),fill=(242,217,159),width=11)
    return True
