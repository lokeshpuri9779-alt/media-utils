"""Story-grounded two-character Pillow acting for ASTRA Studio.

CPU-only, deterministic and no external assets. A single foreground replaces
the existing illustration ONLY if two supported animals occur in the shot.
Artwork stays in the scene contract's 55..1025 x 485..1370 safe region.
"""
from __future__ import annotations

import hashlib
import math
import re

from PIL import ImageDraw

ACTORS = ("fox", "rabbit", "cat", "dog", "owl", "mouse", "otter", "squirrel")
ALIASES = {
    "fox": r"\bfox(?:es)?\b", "rabbit": r"\b(?:rabbit|bunny|hare)s?\b",
    "cat": r"\b(?:cat|kitten)s?\b", "dog": r"\b(?:dog|puppy|puppies)\b",
    "owl": r"\bowls?\b", "mouse": r"\b(?:mouse|mice)\b",
    "otter": r"\botters?\b", "squirrel": r"\bsquirrels?\b",
}
FUR = {
    "fox": (238, 125, 58), "rabbit": (235, 219, 198),
    "cat": (204, 145, 94), "dog": (186, 138, 95),
    "owl": (167, 117, 85), "mouse": (182, 176, 181),
    "otter": (157, 113, 83), "squirrel": (199, 128, 75),
}
INK = (37, 43, 58)
CREAM = (255, 236, 202)
SCENE_BOUNDS = (55, 485, 1025, 1370)
PROPS = {
    "box": r"\b(?:box|parcel|package|gift|present|chest)\b",
    "book": r"\b(?:book|letter|letters|pages|scroll)\b",
    "ball": r"\b(?:ball|orb|marble)\b",
    "flower": r"\b(?:flower|bouquet|rose)\b",
    "lantern": r"\b(?:lantern|lamp|light)\b",
    "key": r"\b(?:key|keys)\b",
    "bell": r"\b(?:bell|chime)\b",
    "compass": r"\b(?:compass|navigation dial)\b",
    "shield": r"\b(?:shield|badge)\b",
    "rocket": r"\b(?:rocket|spaceship)\b",
    "heart": r"\b(?:heart|valentine)\b",
    "wrench": r"\b(?:wrench|spanner)\b",
    "clock": r"\b(?:clock|timepiece)\b",
}


def scene_pair(shot):
    """Return the stable director cast, or named actors in narrated order.

    A story's left/right screen identity must not switch when narration
    reverses the order of the same two animal names between scenes.
    """
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "action")).lower()
    found = []
    for name in ACTORS:
        match = re.search(ALIASES[name], text)
        if match:
            found.append((match.start(), name))
    cast = shot.get("story_cast") or ()
    if isinstance(cast, (list, tuple)) and len(cast) == 2:
        cast = tuple(str(x).lower() for x in cast)
        if all(x in ACTORS for x in cast) and len(set(cast)) == 2:
            # A third named species means this shot may require a different
            # compositor; never misrepresent it as one of the core duo.
            if all(name in cast for _, name in found):
                return cast
            return ()
    if len(found) >= 2:
        return tuple(name for _, name in sorted(found)[:2])
    return ()


def scene_prop(shot):
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "action")).lower()
    found = [(m.start(), name) for name, pattern in PROPS.items()
             if (m := re.search(pattern, text))]
    return min(found)[1] if found else None


def scene_mood(shot):
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "headline", "action")).lower()
    if re.search(r"\b(?:oh no|shocked|surpris\w*|gasp|scream|scared|panic)\b", text):
        return "surprised"
    if re.search(r"\b(?:don't|do not|stop|angry|warn\w*|danger|furious)\b", text):
        return "angry"
    if re.search(r"\b(?:what|why|wonder|mystery|curious|question)\b", text):
        return "curious"
    if re.search(r"\b(?:smile|laugh|celebrat\w*|happy|cheer|dance)\b", text):
        return "happy"
    return {"reveal":"curious", "build":"surprised",
            "twist":"curious","payoff":"happy"}.get(
                str(shot.get("story_beat") or "").lower(), "alert")


def _blend(a, b, k):
    return tuple(round(x * (1-k) + y*k) for x, y in zip(a, b))


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3-2*t)


def _line(d, pts, color, width=9):
    d.line(pts, fill=color, width=width, joint="curve")


def _stage(d, shot, t):
    # Directed scenery uses the narrated location, not a recurring stock scene.
    from astra_v2.pillow_scene_direction import draw_story_stage
    return draw_story_stage(d,shot,t)


def _facial(d, x, y, mood, t, actor_idx):
    blink = abs(math.sin(t*1.7 + actor_idx*.6)) > .985
    for side in (-1, 1):
        ex=x+side*50
        # Expression brows move independently from eyes.
        tilt = {"angry": -side*15, "surprised": -16,
                "curious": side*10, "happy": 4}.get(mood, 0)
        _line(d, [(ex-20, y-81+tilt), (ex+20,y-79-tilt)],
              INK, 7)
        if blink:
            _line(d, [(ex-18,y-34),(ex+18,y-34)], INK, 5)
        else:
            d.ellipse((ex-25,y-64,ex+25,y-13),fill=(255,250,239),outline=INK,width=4)
            look = 5 * (1 if mood=="curious" else 0)
            d.ellipse((ex-7+look,y-49,ex+9+look,y-23),fill=INK)
            d.ellipse((ex-4+look,y-46,ex+1+look,y-40),fill=(255,255,255))
    # Cheeks and nose.
    for side in (-1, 1):
        ex=x+side*84
        d.ellipse((ex-19,y+41,ex+19,y+57),fill=(237,154,141))
    d.ellipse((x-12,y+30,x+12,y+47),fill=INK)
    if mood=="surprised":
        d.ellipse((x-15,y+64,x+15,y+107),fill=(61,39,54))
        d.ellipse((x-7,y+86,x+7,y+100),fill=(185,106,119))
    elif mood=="angry":
        _line(d,[(x-19,y+86),(x+18,y+86)],INK,5)
    else:
        d.arc((x-35,y+50,x+35,y+110), 5, 173, fill=INK, width=5)


def _ears_and_tail(d, actor, x, y, t, fur):
    if actor=="rabbit":
        for side in (-1,1):
            ex=x+side*72
            bend=int(8*math.sin(t*1.4+side))
            d.ellipse((ex-33+bend,y-332,ex+33+bend,y-92),fill=fur,outline=INK,width=5)
            d.ellipse((ex-15+bend,y-303,ex+15+bend,y-111),fill=(244,169,184))
    elif actor=="fox":
        for side in (-1,1):
            ex=x+side*82
            d.polygon(((ex-52,y-100),(ex+side*15,y-242),(ex+46,y-105)),
                      fill=fur)
            d.polygon(((ex-24,y-117),(ex+side*12,y-207),(ex+19,y-111)),
                      fill=(255,191,158))
    elif actor in ("cat","squirrel"):
        for side in (-1,1):
            ex=x+side*83
            d.polygon(((ex-51,y-98),(ex+side*19,y-209),(ex+47,y-105)),fill=fur)
        d.arc((x+86,y+133,x+240,y+370),190,352,fill=fur,width=27)
    elif actor=="dog":
        for side in (-1,1):
            ex=x+side*114
            d.ellipse((ex-50,y-101,ex+50,y+37),fill=(126,87,67))
    elif actor=="mouse":
        for side in (-1,1):
            ex=x+side*105
            d.ellipse((ex-56,y-211,ex+56,y-91),fill=fur,outline=INK,width=4)
            d.ellipse((ex-38,y-193,ex+38,y-108),fill=(234,165,181))
    elif actor=="owl":
        for side in (-1,1):
            ex=x+side*92
            d.polygon(((ex-54,y-112),(ex+side*16,y-212),(ex+55,y-99)),fill=fur)
    else:
        for side in (-1,1):
            ex=x+side*107
            d.ellipse((ex-32,y-129,ex+32,y-33),fill=fur)


def _actor(d, name, x, y, t, action, mood, idx, *, hand_target=None,
           interact_side=1, visual_recipe=None):
    from astra_v2.procedural_visual_library import draw_costume_detail, draw_accessory
    fur=FUR[name]
    if visual_recipe:
        fur=_blend(fur, visual_recipe["fur"], .12 if name in ("fox","rabbit") else .27)
    stride=math.sin(t*(8.4 if action=="run" else 4.6)+idx*math.pi)
    gait=int(43*stride) if action in ("walk","run") else 0
    bob=int(26*abs(math.sin(t*5+idx))) if action=="jump" else int(6*math.sin(t*2+idx))
    y-=bob
    # Ground shadows, tails and articulated legs behind costume.
    d.ellipse((x-103,1267,x+104,1288),fill=(18,48,58))
    if name=="fox":
        sweep=int(22*math.sin(t*2))
        d.polygon(((x+65,y+254),(x+179,y+206+sweep),(x+215,y+270+sweep),
                   (x+158,y+312),(x+76,y+309)),fill=fur,outline=INK,width=4)
        d.polygon(((x+179,y+206+sweep),(x+215,y+270+sweep),(x+186,y+279)),
                  fill=CREAM)
    if name=="otter":
        d.arc((x+74,y+200,x+210,y+375),190,350,fill=fur,width=22)
    for side in (-1,1):
        sx=x+side*54
        step=side*gait
        _line(d,[(sx,y+285),(sx+step//2,y+342),(sx+step,y+406-abs(step)//5)],
              fur, 28)
        shoe=(82,181,179) if idx==0 else (177,143,212)
        d.ellipse((sx+step-32,y+394-abs(step)//5,
                   sx+step+32,y+421-abs(step)//5),fill=shoe)
    costume=(visual_recipe["fabric"] if visual_recipe else
             (60,151,159) if idx==0 else (139,113,178))
    d.rounded_rectangle((x-102,y+102,x+102,y+309),radius=50,
                        fill=costume,outline=INK,width=5)
    d.polygon(((x-50,y+105),(x,y+169),(x+50,y+105)),
              fill=CREAM)
    d.line((x,y+170,x,y+296),fill=(220,202,178),width=4)
    for yy in (197,242):
        d.ellipse((x-6, y+yy-6,x+6,y+yy+6),
                  fill=(245,213,115),outline=INK,width=2)
    if visual_recipe:
        draw_costume_detail(d,x,y,visual_recipe)
    # Jointed arms, with a real end-effector target when holding an object.
    hands=[]
    for side in (-1,1):
        shoulder=(x+side*87,y+150)
        wave=action in ("wave","warn","throw") and side==1
        arm_raise=80*abs(math.sin(t*4.5+idx)) if wave else 0
        hand=(x+side*153,y+218-arm_raise)
        if hand_target is not None and side==interact_side:
            hand=(hand_target[0]-side*22,hand_target[1]+2)
        elbow=((shoulder[0]+hand[0])*.5+side*18,
               (shoulder[1]+hand[1])*.5+14)
        _line(d,[shoulder,elbow,hand],fur,22)
        d.ellipse((hand[0]-13,hand[1]-13,hand[0]+13,hand[1]+13),
                  fill=CREAM,outline=INK,width=3)
        hands.append(hand)
    # Head and features: stable species identity across frames.
    _ears_and_tail(d,name,x,y,t,fur)
    d.ellipse((x-117,y-132,x+117,y+122),fill=fur,outline=INK,width=6)
    if name in ("fox","dog","otter","squirrel"):
        for side in (-1,1):
            ex=x+side*59
            d.ellipse((ex-41,y+42,ex+41,y+106),fill=CREAM)
    if name=="owl":
        for side in (-1,1):
            ex=x+side*51
            d.ellipse((ex-45,y-70,ex+45,y+35),fill=CREAM)
    _facial(d,x,y,mood,t,idx)
    if visual_recipe:
        draw_accessory(d,x,y,visual_recipe)
    return hands


def _prop(d, name, x, y, t, *, symbol_id=None):
    """Draw the narrated object, with an optional stable illustrated emblem."""
    x,y=int(x),int(y)
    if name=="box":
        d.rounded_rectangle((x-79,y-67,x+79,y+67),radius=9,
                            fill=(155,105,65),outline=(72,51,48),width=5)
        d.polygon(((x-77,y-66),(x+76,y-66),(x+65,y-45),(x-66,y-45)),
                  fill=(197,146,92))
        d.line((x,y-65,x,y+67),fill=(244,218,164),width=13)
        d.line((x-73,y+5,x+75,y+5),fill=(244,218,164),width=11)
        d.arc((x-26,y-85,x+26,y-40),0,180,fill=CREAM,width=7)
    elif name=="book":
        d.rounded_rectangle((x-70,y-64,x+70,y+64),radius=9,
                            fill=(174,102,98),outline=INK,width=5)
        d.line((x,y-58,x,y+58),fill=CREAM,width=5)
        for yy in (-25,10,39):
            d.line((x-50,y+yy,x-13,y+yy),fill=(233,211,181),width=3)
    elif name=="ball":
        r=62
        d.ellipse((x-r,y-r,x+r,y+r),fill=(236,186,96),outline=INK,width=5)
        d.arc((x-33,y-40,x+37,y+40),80,290,fill=(245,235,183),width=6)
    elif name=="flower":
        d.line((x,y-10,x,y+70),fill=(78,150,93),width=9)
        for i in range(6):
            a=i*math.pi/3+t*.04
            px=x+29*math.cos(a);py=y-23+29*math.sin(a)
            d.ellipse((px-19,py-19,px+19,py+19),fill=(241,164,172))
        d.ellipse((x-15,y-38,x+15,y-8),fill=(247,216,107))
    elif name=="lantern":
        d.rounded_rectangle((x-49,y-59,x+49,y+66),radius=12,
                            fill=(245,205,116),outline=INK,width=6)
        d.arc((x-32,y-91,x+32,y-33),180,355,fill=CREAM,width=9)
        d.ellipse((x-21,y-25,x+21,y+42),fill=(255,237,174))
    else:
        from astra_v2.procedural_visual_library import draw_icon, icon_for_story
        draw_icon(d,icon_for_story(name,name),x,y,size=120)
        return
    if symbol_id is not None and name in ("box","book","ball","lantern"):
        from astra_v2.procedural_visual_library import draw_icon
        draw_icon(d,symbol_id,x,y+13,size=33)


def prop_position(action, t):
    """Deterministic continuous object travel; never reset a carried prop."""
    action = str(action).lower()
    pickup = action in {"pick","pickup","pick_up","carry","repair","hold"}
    throw = action == "throw"
    progress = _ease((max(0, t)-.15)/.9) if pickup or throw else 0.0
    if throw:
        return (540+int(300*progress), 1140-int(190*math.sin(progress*math.pi)))
    return (int(540*(1-progress)+433*progress),
            int(1216*(1-progress)+1060*progress))


def draw_duo(image, shot, t):
    """Return True only when the complete illustrated duo was drawn."""
    pair=scene_pair(shot)
    if not pair:
        return False
    if image.size != (1080,1920):
        raise ValueError("Pillow duo expects ASTRA 1080x1920 master canvas")
    d=ImageDraw.Draw(image)
    _stage(d,shot,t)
    action=str(shot.get("story_action") or "idle").lower()
    mood=scene_mood(shot)
    prop=scene_prop(shot)
    pickup=action in {"pick","pickup","pick_up","carry","repair","hold"}
    progress=_ease((max(0,t)-.15)/.9) if pickup else 0.0
    from astra_v2.pillow_scene_direction import prop_trajectory, actor_translation
    prop_pos=(prop_trajectory(shot,t) if shot.get("story_beat") else
              prop_position(action,t))
    from astra_v2.procedural_visual_library import (
        character_recipe, visual_identity, icon_for_story, MOTIFS)
    stable_key=shot.get("story_visual_seed") or "|".join(pair)
    for idx,name in enumerate(pair):
        x=(298 if idx==0 else 772)+actor_translation(action,t,idx)
        if idx==1 and action=="carry":
            x-=105
        y=846
        contact=bool(prop and pickup and
                     (progress>.25 or shot.get("story_beat")=="payoff"))
        hand_target=(prop_pos if contact else None)
        actor_mood=mood
        if mood=="angry" and idx==0:
            actor_mood="curious"  # Reaction shot, not two identical emotions.
        if idx==1 and action!="carry":
            hand_target=None
        recipe=character_recipe(visual_identity(stable_key,name,idx))
        _actor(d,name,x,y,t,action,actor_mood,idx,
               hand_target=hand_target,interact_side=1 if idx==0 else -1,
               visual_recipe=recipe)
    if prop:
        motif={"box":"star","ball":"star","flower":"flower",
               "lantern":"sun","book":"book"}.get(prop,prop)
        symbol_id=icon_for_story(motif,stable_key) if motif in MOTIFS else None
        _prop(d,prop,*prop_pos,t,symbol_id=symbol_id)
    return True
