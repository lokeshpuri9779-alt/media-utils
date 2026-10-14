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
    role = str(shot.get("story_beat") or "")
    if role == "reveal":
        return "curious"
    if role == "build":
        return "surprised"
    if role == "twist":
        return "alert"
    if role == "payoff":
        return "happy"
    return "alert"


def _blend(a, b, k):
    return tuple(round(x * (1-k) + y*k) for x, y in zip(a, b))


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3-2*t)


def _line(d, pts, color, width=9):
    d.line(pts, fill=color, width=width, joint="curve")


def scene_setting(shot):
    """Choose a stable story setting from authored title and scene context."""
    text = " ".join(str(shot.get(k) or "") for k in
                    ("story_title", "speech", "visual_prompt", "action")).lower()
    if re.search(r"\b(?:library|chapter|bookshop|bookshelf|bookshelves)\b", text):
        return "library"
    if re.search(r"\b(?:harbor|harbour|lighthouse|pier|boat dock)\b", text):
        return "harbor"
    if re.search(r"\b(?:river|stream|pond|floating|dock|water)\b", text):
        return "river"
    if re.search(r"\b(?:garden|flower|greenhouse|plant|bloom)\b", text):
        return "garden"
    if re.search(r"\b(?:hillside|hill|meadow|mountain|kite)\b", text):
        return "hillside"
    if re.search(r"\b(?:town|market|festival|village|bakery)\b", text):
        return "village"
    return "forest"


def scene_phase(shot):
    """Unique four-beat staging with a deterministic fallback for previews."""
    role = str(shot.get("story_beat") or "").lower()
    return {"reveal": 0, "build": 1, "twist": 2, "payoff": 3}.get(role, 0)


def _stage(d, shot, t):
    """Draw story-specific depth and changing shot accents inside safe zone."""
    text = " ".join(str(shot.get(k) or "") for k in
                    ("story_title", "speech", "visual_prompt", "action")).lower()
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")
    setting = str(shot.get("story_setting") or scene_setting(shot))
    beat = scene_phase(shot)
    night = bool(re.search(r"\b(?:night|moon|stars?|dark|shadow|midnight)\b", text))
    sky = (92, 126, 149) if night else (122, 162, 152)
    far = (56, 99, 112) if night else (85, 135, 121)
    earth = (35, 76, 83) if night else (52, 107, 98)
    # Hero moon/sun shifts perspective across four narrative beats.
    sunx = (260, 700, 460, 790)[beat]
    d.ellipse((sunx-94, 570, sunx+94, 758), fill=sky)
    if setting == "hillside":
        d.polygon([(85, 1184), (245, 790), (475, 1178)], fill=far)
        d.polygon([(390, 1188), (695, 755), (1010, 1188)], fill=(54, 100, 105))
        d.arc((90, 1120, 997, 1430), 185, 340, fill=(94, 161, 129), width=12)
        # A high trail marker gives a different landmark than the flat forest.
        x = 920 if beat < 2 else 135
        d.line((x, 1117, x, 907), fill=(183, 154, 107), width=17)
        d.polygon(((x-55, 915), (x+42, 915), (x+42, 980), (x-55, 980)),
                  fill=(190, 137, 83))
    elif setting in ("river", "harbor"):
        d.polygon([(100, 1113), (310, 921), (475, 1115)], fill=far)
        d.polygon([(680, 1119), (878, 910), (1000, 1117)], fill=(63, 111, 120))
        d.rounded_rectangle((90, 1175, 989, 1347), radius=68,
                            fill=(42, 103, 125))
        for i in range(5):
            x = 133 + i*183 + int(10*math.sin(t*1.1+i))
            d.arc((x, 1210+(i%2)*35, x+140, 1280+(i%2)*35),
                  190, 335, fill=(116, 176, 184), width=6)
        if setting == "harbor":
            for x in (125, 890):
                d.line((x, 930, x, 1220), fill=(140, 126, 101), width=20)
                d.arc((x-26, 925, x+26, 971), 180, 350, fill=(225, 198, 129), width=6)
    elif setting == "library":
        for x in (135, 760):
            d.rounded_rectangle((x, 625, x+196, 1136),
                                radius=15, fill=(102, 81, 89))
            for row in range(3):
                yy = 730+row*130
                d.line((x+18, yy+76, x+180, yy+76),
                       fill=(217, 183, 135), width=10)
                for book in range(7):
                    bx=x+25+book*22
                    bh=64+(seed+row+book)%19
                    d.rectangle((bx, yy+70-bh, bx+15, yy+68),
                                fill=((121+book*15)%210, 121+(row*20)%75, 135+(book*9)%65))
    elif setting == "garden":
        d.polygon([(77, 1180),(370, 886),(625, 1166)],fill=far)
        d.polygon([(600, 1170),(845, 924),(1010, 1188)],fill=(58, 120, 110))
        for i in range(6):
            x=115+i*158
            yy=1157+(i%2)*39
            d.line((x,yy,x,yy+120),fill=(74,140,98),width=11)
            for j in range(5):
                ang=j*(2*math.pi/5)
                px=x+24*math.cos(ang);py=yy+22*math.sin(ang)
                d.ellipse((px-13,py-13,px+13,py+13),fill=(214,146,157))
            d.ellipse((x-12,yy-12,x+12,yy+12),fill=(244,216,115))
    elif setting == "village":
        for i,x in enumerate((96, 410, 782)):
            h=185+((seed+i*29)%75)
            d.polygon(((x,1158-h),(x+98,1068-h),(x+210,1158-h)),
                      fill=(120,109,118))
            d.rounded_rectangle((x,1158-h,x+210,1171),radius=5,
                                fill=(103,143,143))
            d.rectangle((x+83,1133-h,x+127,1197-h),fill=(217,193,125))
    else:
        for idx in range(5):
            x = 107 + (idx*197 + seed%63)%860
            y = 834 + idx%2*65
            d.polygon(((x-97,1140),(x,y),(x+98,1140)),
                      fill=far if idx%2 else (45,93,102))
    # Keep actors grounded and protect all headline/caption regions.
    d.ellipse((70, 1188, 1010, 1361), fill=earth)
    d.ellipse((120, 1234, 970, 1335), fill=(51, 114, 102))
    for i in range(10):
        x=140+(seed//7+i*161)%790
        y=1255+(i%3)*19
        d.arc((x-25,y-16,x+25,y+19),196,342,fill=(103,166,127),width=4)
    for i in range(8):
        x=130+(seed+i*157)%820
        y=590+(i*97)%330
        radius=2+i%3
        drift=int(5*math.sin(t*.85+i))
        d.ellipse((x-radius,y-radius+drift,x+radius,y+radius+drift),
                  fill=(230,218,162) if night else (170,211,191))



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


def _actor(d, name, x, y, t, action, mood, idx, *, hand_target=None):
    fur=FUR[name]
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
    costume=(60,151,159) if idx==0 else (139,113,178)
    d.rounded_rectangle((x-102,y+102,x+102,y+309),radius=50,
                        fill=costume,outline=INK,width=5)
    d.polygon(((x-50,y+105),(x,y+169),(x+50,y+105)),
              fill=CREAM)
    d.line((x,y+170,x,y+296),fill=(220,202,178),width=4)
    for yy in (197,242):
        d.ellipse((x-6, y+yy-6,x+6,y+yy+6),
                  fill=(245,213,115),outline=INK,width=2)
    # Jointed arms, with a real end-effector target when holding an object.
    hands=[]
    for side in (-1,1):
        shoulder=(x+side*87,y+150)
        wave=action in ("wave","warn","throw") and side==1
        arm_raise=80*abs(math.sin(t*4.5+idx)) if wave else 0
        hand=(x+side*153,y+218-arm_raise)
        if hand_target is not None and side==1:
            hand=(hand_target[0]-22,hand_target[1]+2)
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
    return hands


def _prop(d, name, x, y, t):
    """Draw the one narrated physical object. Never invent story props."""
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


def story_prop_position(shot, t):
    """Prop follows the narrated four-beat action, not a fixed screen icon.

    The local scene time is bounded so a long narration doesn't teleport props.
    Ball chase: escape -> pursuit -> catch -> carry.
    Other props retain the existing reliable pickup trajectory.
    """
    prop = scene_prop(shot)
    action = str(shot.get("story_action") or "idle").lower()
    beat = scene_phase(shot)
    p = _ease(max(0.0, float(t)) / 2.2)
    if prop == "ball":
        if beat == 0:
            return (int(380 + 430*p), int(1190 - 34*abs(math.sin(t*3.2))))
        if beat == 1:
            return (int(810 - 455*p), int(1175 - 66*abs(math.sin(t*4.1))))
        if beat == 2:
            return (int(355 + 72*p), int(1184 - 116*p))
        return (427, 1068)
    if prop == "box" and beat < 2 and action not in ("carry","pick","repair"):
        if beat == 0:
            return (int(410+270*p), 1190)
        return (int(680-190*p), 1190)
    if prop == "lantern" and beat == 3:
        return (433, 1060)
    return prop_position(action, t)


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
    prop_pos=story_prop_position(shot,t)
    beat=scene_phase(shot)
    # Characters retain stable left/right identities, but the director changes
    # their blocking as stakes rise and they react to a moving physical prop.
    for idx,name in enumerate(pair):
        x=(290,330,308,280)[beat] if idx == 0 else (800,752,785,802)[beat]
        y=(852,878,855,850)[beat]
        if action in ("run","walk"):
            x += int((1 if idx == 0 else -1)*52*_ease(max(0,t)/2.4))
        elif action == "jump":
            x += int((1 if idx == 0 else -1)*25*_ease(max(0,t)/1.8))
        hand_target=prop_pos if idx==0 and prop and pickup and progress>.25 else None
        actor_mood=mood
        if mood=="angry" and idx==0:
            actor_mood="curious"  # Reaction shot, not two identical emotions.
        _actor(d,name,x,y,t,action,actor_mood,idx,hand_target=hand_target)
    if prop:
        _prop(d,prop,*prop_pos,t)
    return True
