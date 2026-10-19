"""Story-grounded two-character Pillow acting for ASTRA Studio.

CPU-only, deterministic and no external assets. A single foreground replaces
the existing illustration ONLY if two supported animals occur in the shot.
Artwork stays in the scene contract's 55..1025 x 485..1370 safe region.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from PIL import ImageDraw

ACTORS = ("fox", "rabbit", "cat", "dog", "owl", "mouse", "otter", "squirrel", "tapir", "pangolin", "stoat", "lynx", "ferret", "marten")
ALIASES = {
    "fox": r"\bfox(?:es)?\b", "rabbit": r"\b(?:rabbit|bunny|hare)s?\b",
    "cat": r"\b(?:cat|kitten)s?\b", "dog": r"\b(?:dog|puppy|puppies)\b",
    "owl": r"\bowls?\b", "mouse": r"\b(?:mouse|mice)\b",
    "otter": r"\botters?\b", "squirrel": r"\bsquirrels?\b",
    "tapir": r"\btapirs?\b", "pangolin": r"\bpangolins?\b",
    "stoat": r"\bstoats?\b", "lynx": r"\blynx(?:es)?\b",
    "ferret": r"\bferrets?\b", "marten": r"\bmartens?\b",
}
FUR = {
    "fox": (238, 125, 58), "rabbit": (235, 219, 198),
    "cat": (204, 145, 94), "dog": (186, 138, 95),
    "owl": (167, 117, 85), "mouse": (182, 176, 181),
    "otter": (157, 113, 83), "squirrel": (199, 128, 75),
    "tapir": (112, 88, 83), "pangolin": (173, 126, 78),
    "stoat": (225, 212, 182), "lynx": (184, 143, 97),
    "ferret": (190, 159, 119), "marten": (134, 100, 74),
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


@lru_cache(maxsize=2048)
def _cached_actor_mentions(text):
    """All supported animal matches, computed once for a stable shot."""
    found=[]
    for name in ACTORS:
        m=re.search(ALIASES[name],text)
        if m:
            found.append((m.start(),name))
    return tuple(sorted(found))

@lru_cache(maxsize=2048)
def _cached_prop(text):
    found=[(m.start(),name) for name,pattern in PROPS.items()
           if (m:=re.search(pattern,text))]
    return min(found)[1] if found else None

@lru_cache(maxsize=2048)
def _cached_mood(text,role):
    if re.search(r"\b(?:oh no|shocked|surpris\w*|gasp|scream|scared|panic)\b",text):
        return "surprised"
    if re.search(r"\b(?:don't|do not|stop|angry|warn\w*|danger|furious)\b",text):
        return "angry"
    if re.search(r"\b(?:what|why|wonder|mystery|curious|question)\b",text):
        return "curious"
    if re.search(r"\b(?:smil\w*|laugh\w*|celebrat\w*|happ(?:y|ily|iness)|joy\w*|cheer\w*|danc\w*)\b",text):
        return "happy"
    return {"reveal":"curious","build":"surprised",
            "twist":"curious","payoff":"happy"}.get(role,"alert")

def scene_pair(shot):
    """Keep story-level left/right identity, never hide a third named animal."""
    text=" ".join(str(shot.get(k) or "") for k in
                  ("speech","visual_prompt","action")).lower()
    found=_cached_actor_mentions(text)
    cast=shot.get("story_cast") or ()
    # Explicitly empty casts cannot justify inventing characters from prose.
    if "story_cast" in shot and isinstance(shot["story_cast"], (list, tuple)) and not shot["story_cast"]:
        return ()
    # Malformed declared casts must not be bypassed by text inference.
    if "story_cast" in shot and shot["story_cast"] is not None and not isinstance(shot["story_cast"], (list, tuple)):
        return ()
    if isinstance(cast,(list,tuple)) and cast:
        # An explicit cast is authoritative: never discard extra characters
        # and accidentally infer a smaller pair from narration.
        if len(cast) != 2:
            return ()
        cast=tuple(str(x).lower() for x in cast)
        if not (all(x in ACTORS for x in cast) and len(set(cast))==2):
            return ()
        return cast if all(name in cast for _,name in found) else ()
    # Never silently drop a third named species from a supposedly duo shot.
    distinct = tuple(dict.fromkeys(name for _, name in found))
    return distinct if len(distinct) == 2 else ()

def scene_prop(shot):
    # An explicitly authored prop identity takes precedence over incidental
    # mentions in narration. This keeps a carried/repaired object stable when
    # later beats introduce another object (e.g. a key beside a gift).
    declared = shot.get("story_prop")
    if declared is not None:
        name = str(declared).lower().strip()
        if name not in PROPS:
            from astra_errors import CreativeReject
            raise CreativeReject("Studio story prop is not representable: " + name[:60])
        return name
    text=" ".join(str(shot.get(k) or "") for k in
                  ("speech","visual_prompt","action")).lower()
    return _cached_prop(text)

def scene_mood(shot):
    text=" ".join(str(shot.get(k) or "") for k in
                  ("speech","visual_prompt","headline","action")).lower()
    return _cached_mood(text,str(shot.get("story_beat") or "").lower())


def _blend(a, b, k):
    return tuple(round(x * (1-k) + y*k) for x, y in zip(a, b))


def _ease(t):
    from astra_v2.story_motion import smoothstep
    return smoothstep(t)


def _line(d, pts, color, width=9):
    d.line(pts, fill=color, width=width, joint="curve")


def _stage(d, shot, t):
    # Directed scenery uses the narrated location, not a recurring stock scene.
    from astra_v2.pillow_scene_direction import draw_story_stage
    return draw_story_stage(d,shot,t)


def _facial(d, x, y, mood, t, actor_idx):
    from astra_v2.story_motion import evaluate
    # Optimized Pillow's deterministic blink profile avoids per-frame random
    # motion and gives each actor an independent phase.
    blink = evaluate(t + actor_idx * .31).blink
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
    elif actor=="cat":
        for side in (-1,1):
            ex=x+side*83
            d.polygon(((ex-51,y-98),(ex+side*19,y-209),(ex+47,y-105)),fill=fur)
        # Cats have a compact curved tail; keep it distinct from the
        # squirrel's oversized plume so silhouettes remain species-readable.
        d.arc((x+86,y+133,x+220,y+330),190,352,fill=fur,width=25)
    elif actor=="squirrel":
        for side in (-1,1):
            ex=x+side*83
            d.polygon(((ex-51,y-98),(ex+side*19,y-209),(ex+47,y-105)),fill=fur)
        # Solid tapered plume rather than an open wire-loop silhouette.
        d.ellipse((x+110,y+82,x+292,y+287),fill=fur,outline=INK,width=5)
        d.ellipse((x+146,y+116,x+256,y+238),fill=CREAM)
        d.ellipse((x+195,y+152,x+271,y+242),fill=fur)
        d.polygon(((x+83,y+264),(x+147,y+205),(x+190,y+248),
                   (x+129,y+310)),fill=fur)
    elif actor=="dog":
        for side in (-1,1):
            ex=x+side*114
            d.ellipse((ex-50,y-101,ex+50,y+37),fill=(126,87,67))
    elif actor=="mouse":
        for side in (-1,1):
            ex=x+side*105
            d.ellipse((ex-56,y-211,ex+56,y-91),fill=fur,outline=INK,width=4)
            d.ellipse((ex-38,y-193,ex+38,y-108),fill=(234,165,181))
    elif actor in ("lynx", "marten"):
        for side in (-1,1):
            ex=x+side*82
            d.polygon(((ex-47,y-95),(ex+side*23,y-226),(ex+45,y-101)),
                      fill=fur,outline=INK)
            if actor=="lynx":
                d.line((ex+side*23,y-225,ex+side*29,y-259),fill=INK,width=9)
        if actor=="marten":
            d.arc((x+84,y+136,x+224,y+348),180,352,fill=fur,width=30)
    elif actor=="tapir":
        for side in (-1,1):
            ex=x+side*103
            d.ellipse((ex-39,y-173,ex+39,y-61),fill=fur,outline=INK,width=4)
            d.ellipse((ex-21,y-147,ex+21,y-79),fill=(200,155,149))
    elif actor=="pangolin":
        for side in (-1,1):
            ex=x+side*83
            d.ellipse((ex-44,y-162,ex+44,y-79),fill=fur,outline=INK,width=4)
        d.arc((x+83,y+128,x+264,y+365),155,353,fill=fur,width=42)
    elif actor in ("stoat", "ferret"):
        for side in (-1,1):
            ex=x+side*82
            d.ellipse((ex-30,y-182,ex+30,y-91),fill=fur,outline=INK,width=4)
        d.arc((x+75,y+153,x+227,y+342),165,352,fill=fur,width=24)
        if actor=="stoat":
            d.ellipse((x+207,y+299,x+246,y+343),fill=INK)
    elif actor=="owl":
        # Low rounded crown feathers, not cat-like pointed ears.
        for side in (-1,1):
            ex=x+side*72
            d.ellipse((ex-38,y-145,ex+38,y-84),fill=fur,outline=INK,width=4)
    else:
        for side in (-1,1):
            ex=x+side*107
            d.ellipse((ex-32,y-129,ex+32,y-33),fill=fur)


def _actor(d, name, x, y, t, action, mood, idx, *, hand_target=None,
           interact_side=1, visual_recipe=None, ground_y=1267,
           hand_strength=1.0):
    from astra_v2.procedural_visual_library import draw_costume_detail, draw_accessory
    fur=FUR[name]
    if visual_recipe:
        fur=_blend(fur, visual_recipe["fur"], .12 if name in ("fox","rabbit") else .27)
    stride=math.sin(t*(8.4 if action in ("run","chase") else 3.4 if action=="sneak" else 4.6)+idx*math.pi)
    gait=int((51 if action=="chase" else 21 if action=="sneak" else 43)*stride) if action in ("walk","run","chase","sneak","dance","carry") else 0
    if action=="swim":
        gait=int(25*math.sin(t*6.0+idx*math.pi))
    if action=="dance":
        gait=int(34*math.sin(t*6.2+idx*math.pi))
    bob=(int(92*math.sin(math.pi*min(1.0,max(0.0,float(t)%1.2/1.2)))**2) if action=="jump" else
         int(17*math.sin(t*4.2+idx)) if action=="swim" else
         int(6*math.sin(t*2+idx)))
    if action=="dance":
        bob=int(18*abs(math.sin(t*6.2+idx*math.pi)))
    y-=bob
    # Keep feet in world-space contact while the torso subtly bobs.
    # The torso/head use the animated y; leg endpoints use the unbobbed base.
    leg_y=(y+bob if action in ("idle","walk","run","chase","sneak","carry") else y)
    # Ground shadows, tails and articulated legs behind costume.
    # Studio draws actors directly at 1080p, while the experimental ensemble
    # draws them into local transparent sprites. Ground shadows must use the
    # matching coordinate system or get clipped out of every ensemble frame.
    shadow_half_width=max(62,103-int(max(0,bob)*.28)) if action=="jump" else 103
    d.ellipse((x-shadow_half_width,ground_y-10,x+shadow_half_width,ground_y+11),fill=(18,48,58))
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
        # Lift a foot only on its forward swing; keep the planted foot
        # at ground height through the opposite half of the stride.
        lift=(int(24*max(0.0,side*stride)) if action in
              ("walk","run","chase","sneak","carry") else abs(step)//5)
        _line(d,[(sx,leg_y+285),(sx+step//2,leg_y+342-lift//2),
                 (sx+step,leg_y+406-lift)],fur,28)
        shoe=(82,181,179) if idx==0 else (177,143,212)
        d.ellipse((sx+step-32,leg_y+394-lift,
                   sx+step+32,leg_y+421-lift),fill=shoe)
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
        wave=action in ("wave","warn","throw","point") and side==1
        arm_raise=80*abs(math.sin(t*4.5+idx)) if wave else 0
        if action=="dance":
            arm_raise=45+48*math.sin(t*6.2+idx*math.pi+(0 if side==1 else math.pi))
        if action=="swim":
            arm_raise=45*math.sin(t*7+idx*math.pi+(0 if side==1 else math.pi))
        hand=(x+side*153,y+218-arm_raise)
        if wave:
            # Raise the waving hand above the head; the old 80px offset
            # never lifted it past the shoulder, making waves unreadable.
            phase=math.sin(t*5.5+idx)
            hand=(x+126+int(24*phase),y-115+int(18*phase))
        elif action=="dance":
            # Opposing overhead gestures create a recognizable dance pose.
            phase=math.sin(t*6.2+idx*math.pi)
            hand=(x+side*(120+int(18*phase)),y+18-int(95*max(0,side*phase)))
        if action in ("walk","run","chase","sneak"):
            # Counter-swing the arms against the leg gait. Opposite arms
            # advance together with opposite legs, rather than hanging still.
            swing=math.sin(t*(8.4 if action in ("run","chase") else
                             3.4 if action=="sneak" else 4.6)+idx*math.pi)
            extent=52 if action in ("run","chase") else 19 if action=="sneak" else 32
            hand=(x+side*153,y+218+int(side*extent*swing))
        if action=="catch" and side==1:
            hand=(x+176,y+118)
        elif action=="sneak":
            hand=(x+side*125,y+235+int(side*19*stride))
        elif action=="point" and side==1:
            hand=(x+185,y+112)
        elif action=="clap":
            hand=(x+side*(33+25*abs(math.sin(t*8))),y+173)
        elif action=="hug":
            hand=(x+side*44,y+172)
        elif action in ("push","pull") and side==interact_side:
            hand=(x+side*157,y+225+int(9*math.sin(t*4)))
        if hand_target is not None and side==interact_side:
            # Ease a reach toward a prop instead of snapping the wrist when
            # contact begins or ends. Default 1.0 preserves Studio duo poses.
            strength=_ease(float(hand_strength))
            target=(hand_target[0]-side*22, hand_target[1]+2)
            hand=(hand[0]*(1-strength)+target[0]*strength,
                  hand[1]*(1-strength)+target[1]*strength)
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
        # Wide facial discs and brow arcs make the owl readable at Shorts scale.
        for side in (-1,1):
            ex=x+side*52
            d.ellipse((ex-54,y-86,ex+54,y+49),fill=CREAM)
            d.arc((ex-50,y-88,ex+50,y+37),190,350,fill=INK,width=5)
    _facial(d,x,y,mood,t,idx)
    if name=="tapir":
        # Downturned flexible snout, visibly unlike the generic rounded face.
        d.rounded_rectangle((x-30,y+48,x+44,y+168),radius=30,
                            fill=fur,outline=INK,width=5)
        d.ellipse((x+13,y+144,x+26,y+155),fill=INK)
    elif name=="pangolin":
        # Overlapping scales along the crown and shoulders.
        for row in range(3):
            for col in range(5-row):
                px=x-87+col*43+row*21
                py=y-108+row*35
                d.arc((px-20,py-13,px+21,py+30),5,175,
                      fill=(95,68,47),width=5)
    elif name=="lynx":
        for side in (-1,1):
            d.line((x+side*83,y+63,x+side*130,y+88),fill=INK,width=4)
    elif name in ("ferret","marten","stoat"):
        d.ellipse((x-72,y-22,x-25,y+32),fill=(84,64,59))
        d.ellipse((x+25,y-22,x+72,y+32),fill=(84,64,59))
    # Species-specific facial markers supplement the shared expressive face.
    if name=="owl":
        d.polygon(((x-22,y+35),(x+22,y+35),(x,y+72)),
                  fill=(242,170,61),outline=INK)
    elif name in ("cat","mouse"):
        # Fine, symmetric whiskers remain inside the scene's safe region.
        for side in (-1,1):
            start=x+side*76
            end=x+side*143
            for offset in (-4,13,29):
                _line(d,[(start,y+47+offset),(end,y+35+offset)],
                      INK,3)
    if visual_recipe:
        draw_accessory(d,x,y,visual_recipe)
    return hands


def _prop(d, name, x, y, t, *, symbol_id=None, action="idle"):
    """Draw the narrated object, with an optional stable illustrated emblem."""
    x,y=int(x),int(y)
    if name=="box":
        d.rounded_rectangle((x-79,y-67,x+79,y+67),radius=9,
                            fill=(155,105,65),outline=(72,51,48),width=5)
        opened=_ease((max(0,t)-.15)/.85) if action=="open" else 0.0
        rise=int(opened*74)
        d.polygon(((x-77,y-66-rise),(x+76,y-66-rise),
                   (x+65,y-45-rise),(x-66,y-45-rise)),
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
    pickup = action in {"pick","pickup","pick_up","carry","repair","hold","catch"}
    throw = action == "throw"
    progress = _ease((max(0, t)-.15)/.9) if pickup or throw or action in ("push","pull") else 0.0
    if action=="push":
        return (540+round(125*progress),1216)
    if action=="pull":
        return (540-round(125*progress),1216)
    if action=="catch":
        return (750-round(320*progress),1145-round(90*progress)-round(68*math.sin(progress*math.pi)))
    if throw:
        return (540+int(300*progress), 1140-int(190*math.sin(progress*math.pi)))
    return (int(540*(1-progress)+433*progress),
            int(1216*(1-progress)+1060*progress))


def duo_compatibility(shot):
    """Check scene suitability before rendering; no invented animal partners."""
    pair = scene_pair(shot)
    if not pair:
        return {"supported": False, "reason": "requires_two_supported_animals", "cast": ()}
    return {"supported": True, "reason": "supported", "cast": pair}


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
    from astra_v2.pillow_scene_direction import prop_trajectory, actor_translation
    prop_pos=(prop_trajectory(shot,t)
              if shot.get("story_beat") and action not in ("push","pull","open")
              else prop_position(action,t))
    from astra_v2.procedural_visual_library import (
        character_recipe, visual_identity, icon_for_story, MOTIFS)
    stable_key=shot.get("story_visual_seed") or "|".join(pair)
    # Physical hand contact: once grasped, the object is driven by the
    # actor's hand anchor rather than an unrelated overlay trajectory.
    contact_actions={"pick","pickup","pick_up","carry","hold","repair","catch"}
    # Release transitions smoothly back to the staged prop position instead
    # of snapping away from the hand on the first release frame.
    if prop and action in ("release","drop","put_down"):
        release=_ease((max(0.0,float(t))-.15)/.55)
        actor_x=298+actor_translation(action,t,0)
        held=(actor_x+175-22,846+215+2)
        staged=prop_trajectory(shot,t) if shot.get("story_beat") else (433,1060)
        prop_pos=(round(held[0]*(1-release)+staged[0]*release),
                  round(held[1]*(1-release)+staged[1]*release))
    if prop and action in ("push","pull"):
        # Begin contact before object travel so the hand does not chase a
        # moving prop; ease the object only after the reach phase.
        travel=_ease((max(0.0,float(t))-.42)/.85)
        displacement=round((125 if action=="push" else -125)*travel)
        prop_pos=(540+displacement,1216)
    if prop and action in contact_actions:
        # A smooth, monotonic grasp phase avoids the prop drifting back
        # toward its staging point after contact has been established.
        grasp=_ease((max(0.0,float(t))-.15)/.9)
        actor_x=298+actor_translation(action,t,0)
        # Match the actual right-hand target used by _actor (target x - 22).
        # Without this offset, the held object floats away from the palm.
        held=(actor_x+175-22, 846+215+2)
        prop_pos=(round(prop_pos[0]*(1-grasp)+held[0]*grasp),
                  round(prop_pos[1]*(1-grasp)+held[1]*grasp))
    for idx,name in enumerate(pair):
        x=(298 if idx==0 else 772)+actor_translation(action,t,idx)
        if idx==1 and action=="carry":
            x-=105
        y=846
        # A story prop may be picked up, repaired, opened, pushed or pulled.
        # The previous threshold abruptly snapped the wrist into place, and
        # accidentally excluded push/pull entirely because pickup was False.
        # Blend contact from the first reach through a smooth extension.
        interact_actions={"pick","pickup","pick_up","carry","repair",
                          "hold","open","push","pull","catch","release","drop","put_down"}
        hand_strength=(_ease((max(0.0,float(t))-.06)/.86)
                       if prop and action in interact_actions else 0.0)
        # After releasing a prop, withdraw the wrist instead of following
        # the object all the way to its resting position.
        if action in ("release","drop","put_down"):
            hand_strength *= 1.0-_ease((max(0.0,float(t))-.45)/.75)
        hand_target=prop_pos if hand_strength>0 else None
        actor_mood=mood
        if mood=="angry" and idx==0:
            actor_mood="curious"  # Reaction shot, not two identical emotions.
        if idx==1 and action!="carry":
            hand_target=None
        recipe=character_recipe(visual_identity(stable_key,name,idx))
        _actor(d,name,x,y,t,action,actor_mood,idx,
               hand_target=hand_target,hand_strength=hand_strength,
               interact_side=1 if idx==0 else -1,
               visual_recipe=recipe)
    if prop:
        motif={"box":"star","ball":"star","flower":"flower",
               "lantern":"sun","book":"book"}.get(prop,prop)
        symbol_id=icon_for_story(motif,stable_key) if motif in MOTIFS else None
        _prop(d,prop,*prop_pos,t,symbol_id=symbol_id,action=action)
    return True
