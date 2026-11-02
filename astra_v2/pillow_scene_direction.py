"""Deterministic scene direction for the CPU-only Pillow duo renderer.

Narrated locations drive a SMALL set of different illustrated environments.
No network/media calls, no new engine, no overlays in caption/headline regions.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

GROUND_TOP = 1180

SCENE_CUES = (
    # Handheld books, pages and curtains are objects, not locations. Never
    # change the whole set to a library just because a character holds a book.
    ("observatory", r"\b(?:observatory|telescope|planetarium|astronomer)\b"),
    ("railway", r"\b(?:railway|railroad|train station|locomotive|rail tracks?)\b"),
    ("museum", r"\b(?:museum|gallery|exhibit|exhibition)\b"),
    ("workshop", r"\b(?:workshop|factory|forge|repair shop|mechanical room)\b"),
    ("cavern", r"\b(?:cave|cavern|underground|echo vault|crystal chamber)\b"),
    ("mangrove", r"\b(?:mangrove|swamp|wetland|marsh|bayou)\b"),
    ("desert", r"\b(?:desert|dunes?|oasis|sandstorm|arid)\b"),
    ("library", r"\b(?:library|bookshelf|shelves|bookcase|reading room)\b"),
    ("harbor", r"\b(?:harbor|harbour|pier|dock|seawall|fishing boats?)\b"),
    # Water, floating objects and tides are not sufficient evidence of a
    # location change: a village fountain or a floating gift must not teleport
    # the cast to a river. Require an actual water-body location cue.
    ("river", r"\b(?:river|stream|pond|creek|canal|lake|inlet|riverbank|river bank|lakeshore)\b"),
    # A flower carried through a village should not teleport the cast into a
    # garden; only location-specific terms select that illustrated set.
    ("garden", r"\b(?:garden|flowerbed|greenhouse|botanical garden)\b"),
    ("village", r"\b(?:village|market|fountain|square|festival|picnic|street|stall)\b"),
    ("meadow", r"\b(?:meadow|field|grassland|flat clearing)\b"),
    ("hill", r"\b(?:hillside|hill|rocky|rocks?|winding path|ridge|mountain|slope)\b"),
    ("winter", r"\b(?:winter|snow|icy|frost|frozen)\b"),
    ("night", r"\b(?:night|moon|stars?|dark|midnight|shadow)\b"),
    ("forest", r"\b(?:forest|woodland|woods|trees?|leaves|branch|oak)\b"),
)


def story_setting(shot):
    """Choose the explicitly narrated setting, then directed setting."""
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "headline")).lower()
    return _cached_scene_setting(text,str(shot.get("story_environment") or "").lower().strip())

@lru_cache(maxsize=2048)
def _cached_scene_setting(text,direct):
    # Explicitly spoken locations outrank the storyboard suggestion (e.g.
    # "in a library" beats an earlier harbor setting). Handheld objects are
    # intentionally excluded from SCENE_CUES so they cannot cause set swaps.
    for name,pattern in SCENE_CUES:
        if re.search(pattern,text):
            return name
    # No explicit setting in the line: maintain the authored location rather
    # than injecting the default forest every time a character says "book".
    return direct if direct in {key for key,_ in SCENE_CUES} else "meadow"

def _text_seed(shot):
    # Preserve scenery positions, sky decorations and landmarks across beats.
    # Narration and headlines change every beat; they must NOT reseed scenery.
    source = str(shot.get("story_visual_seed") or "").strip()
    if not source:
        source = " ".join(str(shot.get(k) or "") for k in ("speech", "headline"))
    return _cached_stage_seed(source)

@lru_cache(maxsize=2048)
def _cached_stage_seed(source):
    return int.from_bytes(hashlib.sha256(source.encode()).digest()[:4], "big")


def _line(d, xy, color, width=5):
    d.line(xy, fill=color, width=width, joint="curve")


def draw_story_stage(d, shot, t):
    """Background features only in x=55..1025, y=485..1370 stage bounds."""
    setting = story_setting(shot)
    seed = _text_seed(shot)
    nighttime = setting == "night" or bool(re.search(
        r"\b(?:midnight|moonlight|at night|after dark)\b",
        str(shot.get("speech") or "").lower()))
    sky = (74, 109, 153) if nighttime else (96, 157, 165)
    ground = (41, 75, 88) if setting in ("river", "harbor") else (53, 100, 91)
    # Midground silhouettes differ by location and follow the stated setting.
    d.ellipse((530, 555, 765, 790), fill=(132, 163, 181) if nighttime else sky)
    if setting in ("river", "harbor"):
        for y, fill in [(1040,(54,115,151)),(1118,(49,130,155)),(1187,(45,112,137))]:
            d.polygon([(60,y+40),(235,y+12),(460,y+42),
                       (687,y+9),(1025,y+37),(1025,y+97),(60,y+97)],fill=fill)
        for i in range(6):
            x = 135+i*151
            drift=int(8*math.sin(t*.9+i))
            _line(d,[(x,1120+drift),(x+75,1120+drift)],(155,209,221),5)
        if setting == "harbor":
            d.polygon([(100,1105),(452,1105),(420,1158),(112,1158)],fill=(144,109,80))
            for x in (120,275,430):
                d.rectangle((x,1140,x+18,1270),fill=(108,86,71))
            d.polygon([(750,990),(816,927),(882,990)],fill=(222,219,171))
            d.polygon([(733,1070),(899,1070),(861,1112),(770,1112)],fill=(112,89,76))
    elif setting == "observatory":
        d.ellipse((260,560,820,1120),fill=(81,104,147),outline=(204,191,163),width=12)
        for radius in (120,190,258):
            d.arc((540-radius,820-radius,540+radius,820+radius),
                  195,345,fill=(193,197,210),width=6)
        d.polygon(((420,1040),(480,840),(560,805),(595,854),(505,1060)),
                  fill=(176,182,193),outline=(60,71,91))
        d.ellipse((560,792,675,850),fill=(64,81,116),outline=(221,202,165),width=9)
        d.rectangle((500,1050,585,1160),fill=(93,100,118))
    elif setting == "railway":
        for yy in (1045,1130):
            d.line((65,yy,1025,yy),fill=(190,180,166),width=17)
        for x in range(90,1030,95):
            d.rectangle((x,1028,x+28,1160),fill=(115,89,73))
        d.rounded_rectangle((150,715,885,1015),radius=32,
                            fill=(130,86,89),outline=(221,190,149),width=12)
        for x in (220,430,640):
            d.rounded_rectangle((x,760,x+155,902),radius=18,
                                fill=(109,164,184),outline=(230,211,177),width=8)
        for x in (280,750):
            d.ellipse((x-65,972,x+65,1102),fill=(57,64,77),outline=(201,175,130),width=12)
    elif setting == "museum":
        for x in (100,395,690):
            d.rectangle((x,630,x+255,960),fill=(114,104,130),outline=(220,181,116),width=16)
            d.polygon(((x+45,850),(x+125,685),(x+210,850)),
                      fill=(166,150,117))
        d.rectangle((300,1050,780,1180),fill=(166,149,134))
        d.ellipse((440,875,640,1070),fill=(188,171,140),outline=(81,82,90),width=7)
    elif setting == "workshop":
        for x in (95,710):
            d.rectangle((x,670,x+265,1060),fill=(85,98,111),outline=(178,150,121),width=12)
            for k in range(4):
                xx=x+35+k*55
                d.line((xx,730,xx+25,825),fill=(195,174,135),width=12)
        d.rounded_rectangle((330,1040,750,1150),radius=14,fill=(158,112,79))
        for x in (400,540,670):
            d.ellipse((x-42,900,x+42,984),fill=(121,137,146),outline=(56,69,83),width=9)
    elif setting == "cavern":
        d.polygon(((60,620),(180,820),(280,650),(410,865),(550,600),
                   (680,820),(850,650),(1020,835),(1020,1130),(60,1130)),
                  fill=(76,84,116))
        for x in (190,490,810):
            d.polygon(((x-80,1130),(x,850),(x+90,1130)),
                      fill=(115,168,190),outline=(68,104,133))
    elif setting == "mangrove":
        for i in range(5):
            x=135+i*198
            d.ellipse((x-110,655,x+115,840),fill=(48,117,93))
            d.line((x,820,x,1135),fill=(100,80,65),width=22)
            for side in (-1,1):
                d.line((x,945,x+side*85,1150),fill=(116,87,70),width=12)
        d.polygon(((60,1100),(290,1085),(490,1110),(780,1080),(1020,1105),
                   (1020,1190),(60,1190)),fill=(64,134,142))
    elif setting == "desert":
        d.ellipse((800,590,930,720),fill=(248,207,129))
        for i in range(4):
            x=80+i*275
            d.ellipse((x-125,915+i%2*55,x+390,1220+i%2*55),
                      fill=(199,150,100) if i%2 else (228,184,121))
        for x in (230,825):
            d.line((x,980,x,1130),fill=(73,128,96),width=19)
            d.arc((x-55,970,x+12,1060),5,95,fill=(73,128,96),width=14)
    elif setting == "library":
        d.rounded_rectangle((98,540,445,1130),radius=12,fill=(95,83,91),outline=(166,138,111),width=9)
        d.rounded_rectangle((635,540,989,1130),radius=12,fill=(95,83,91),outline=(166,138,111),width=9)
        for shelf_x in (110,650):
            for row in range(4):
                yy=615+row*125
                d.rectangle((shelf_x,yy+70,shelf_x+314,yy+82),fill=(182,136,87))
                for i in range(11):
                    x=shelf_x+10+i*26
                    color=[(186,108,92),(106,155,147),(201,169,102),(142,120,165)][(i+row)%4]
                    d.rectangle((x,yy,x+17,yy+70),fill=color)
        d.rounded_rectangle((455,589,624,956),radius=65,fill=(124,166,189),outline=(229,202,170),width=10)
        d.line((540,610,540,948),fill=(226,211,184),width=8)
    elif setting in ("village",):
        for i in range(4):
            x=75+i*258
            roof=690+(i%2)*44
            d.rectangle((x,roof+95,x+224,1112),fill=(120,134,139))
            d.polygon([(x-10,roof+95),(x+110,roof),(x+235,roof+95)],fill=(171,113,104))
            d.rectangle((x+35,roof+149,x+103,roof+230),fill=(187,205,189))
        if "fountain" in str(shot.get("speech") or "").lower():
            d.ellipse((424,1025,657,1150),fill=(56,121,161))
            d.line((540,1030,540,940),fill=(173,204,204),width=9)
            d.arc((490,925,590,1030),185,355,fill=(160,210,234),width=8)
    elif setting == "garden":
        for i in range(3):
            x=145+i*282
            d.rounded_rectangle((x,1015,x+215,1140),radius=25,fill=(116,87,73))
            for j in range(4):
                fx=x+29+j*47
                d.line((fx,1035,fx,962),fill=(101,178,113),width=7)
                col=[(244,178,183),(248,214,114),(154,191,229)][(i+j)%3]
                d.ellipse((fx-24,928,fx+24,976),fill=col)
                d.ellipse((fx-8,946,fx+8,962),fill=(237,223,152))
        for i in range(5):
            d.ellipse((120+i*185,780+i%2*40,207+i*185,908+i%2*40),fill=(59,119,108))
    else:
        # Forest, night, hill, meadow and winter use genuinely different
        # landmarks rather than a repeat of the same four triangles.
        hill_fill = ((73,112,144) if setting == "winter"
                     else (51,109,101) if setting == "meadow"
                     else (66,113,113))
        for i in range(3):
            x=75+i*345
            d.ellipse((x-95,890+i%2*50,x+415,1240+i%2*50),fill=hill_fill)
        if setting == "hill":
            d.polygon([(65,1177),(370,950),(540,1155),(820,880),(1025,1160),(1025,1197),(55,1197)],
                      fill=(81,114,109))
            for i in range(7):
                x=155+i*125
                d.ellipse((x-26,1124+(i%2)*22,x+29,1152+(i%2)*22),fill=(124,132,126))
        elif setting in ("forest","night"):
            for i in range(5):
                x=95+i*211
                h=790+(seed+i*19)%120
                d.rectangle((x+22,h+172,x+55,1115),fill=(105,91,76))
                d.polygon([(x-55,h+175),(x+37,h-10),(x+132,h+175)],fill=(38,104,103))
                d.polygon([(x-42,h+105),(x+37,h-50),(x+118,h+105)],fill=(42,120,106))
        elif setting == "winter":
            for i in range(7):
                x=100+i*140
                d.ellipse((x-18,1092+i%2*20,x+26,1109+i%2*20),fill=(208,224,229))
            for i in range(6):
                x=170+i*142
                d.ellipse((x,760+(i*47)%180,x+8,768+(i*47)%180),fill=(218,229,242))
        elif setting == "meadow":
            for i in range(16):
                x=90+i*60
                yy=1088+(i%3)*18
                d.arc((x-25,yy-20,x+25,yy+20),195,340,fill=(107,181,121),width=5)
    d.ellipse((65,1215,1025,1340),fill=ground)
    d.ellipse((120,1235,975,1315),fill=(64,115,102) if setting!="harbor" else (51,110,117))
    # An explicitly narrated broken plank needs a recognizable hazard, not
    # merely a blue river platform. Draw it behind the actors, inside the
    # established artwork-safe region; do not infer damage from "bridge" alone.
    spoken = str(shot.get("speech") or "").lower()
    if setting == "river" and re.search(r"\bbridge\b", spoken) and re.search(r"\bbroken plank\b", spoken):
        wood = (174, 125, 83)
        edge = (97, 72, 62)
        # Keep the missing plank to the right of the central lantern, which
        # otherwise occludes the gap in the final composited Shorts frame.
        # Both decks and the hazard remain within the artwork-safe region.
        for x0, x1 in ((90, 510), (700, 990)):
            d.rectangle((x0, 1140, x1, 1194), fill=wood, outline=edge, width=7)
            for x in range(x0 + 66, x1, 68):
                d.line((x, 1143, x, 1191), fill=edge, width=5)
        d.polygon(((489, 1142), (520, 1154), (503, 1175), (514, 1191),
                   (488, 1191)), fill=(127, 91, 67))
        d.polygon(((717, 1142), (684, 1151), (701, 1173), (686, 1191),
                   (720, 1191)), fill=(127, 91, 67))
        for x in (125, 930):
            d.rectangle((x, 1025, x + 19, 1140), fill=edge)
        d.line((135, 1055, 498, 1055), fill=(196, 157, 108), width=11)
        d.line((709, 1055, 940, 1055), fill=(196, 157, 108), width=11)
    # Story-seeded, fixed environmental dressing: each location has a
    # foreground/midground silhouette. The details never re-roll per frame.
    for k in range(7):
        x=95+(seed//(k+1)+k*151)%890
        y=1070+(k%3)*41
        if setting in ("forest","night","garden","meadow"):
            d.line((x,y+24,x+4,y-15),fill=(81,146,103),width=5)
            d.ellipse((x-10,y-20,x+16,y+3),
                      fill=((199,158,115) if k%2 else (145,186,134)))
        elif setting in ("village","library","hill"):
            d.rounded_rectangle((x-11,y-5,x+17,y+16),radius=4,
                                fill=(131,117,109))
        elif setting in ("river","harbor"):
            d.line((x-20,y,x+24,y),fill=(133,187,196),width=4)
        elif setting=="winter":
            d.ellipse((x-9,y-9,x+12,y+10),fill=(211,229,234))
    # Foreground micro-movement is subtle and secondary to the character rig.
    for i in range(9):
        x=120+(seed+i*137)%825
        y=575+(i*79)%315
        delta=int(4*math.sin(t*.8+i))
        d.ellipse((x-3,y-3+delta,x+3,y+3+delta),fill=(230,218,168) if nighttime else (177,207,186))
    return setting


def actor_translation(action, t, index):
    """Body translation is separate from limb gait, not global camera movement."""
    if action not in ("run","walk","chase","sneak","swim","carry"):
        return 0
    amplitude = {"run":85,"walk":44,"chase":155,"sneak":32,"swim":65,"carry":62}[action]
    elapsed=max(0.0,min(float(t),2.4))/2.4
    follow=(1.0 if action=="carry" else .2 if action=="chase" else .55) if index else 1.0
    return int(amplitude*elapsed*follow)


def prop_trajectory(shot, t):
    """A story object changes place according to the narrated action."""
    speech=str(shot.get("speech") or "").lower()
    role=str(shot.get("story_beat") or "").lower()
    action=str(shot.get("story_action") or "").lower()
    time=max(0,float(t))
    progress=min(1,time/.95)
    progress=progress*progress*(3-2*progress)
    # When the twist explicitly catches the object, contact wins over the
    # earlier rolling/drifting verb in the same spoken sentence.
    if role in ("twist", "payoff") and action in ("carry","pick","repair","hold","catch"):
        return (int(540-110*progress),int(1216-161*progress)) if role=="twist" else (430,1055)
    if action=="catch":
        return (750-round(320*progress),1145-round(90*progress)-round(68*math.sin(progress*math.pi)))
    mode=_cached_prop_verb(speech)
    if mode=="roll":
        x=250+int(min(time,2.2)*205)
        y=1180-int(45*abs(math.sin(time*4.4)))
        return x,y
    if mode=="drift":
        return 235+int(min(time,2.2)*177),1148+int(12*math.sin(time*3))
    if role=="payoff" and action=="carry":
        return (430,1055)
    if action in ("carry","pick","repair","hold"):
        return (int(540-110*progress),int(1216-161*progress))
    if action=="throw":
        return (int(490+335*progress),int(1150-180*math.sin(progress*math.pi)))
    return (540,1216)


@lru_cache(maxsize=2048)
def _cached_prop_verb(speech):
    """Motion verb lookup once per beat rather than every 1/30 second."""
    if re.search(r"\b(?:roll|rolled|rolling|runaway|bounced|bounce)\b",speech):
        return "roll"
    if re.search(r"\b(?:drift|drifted|floating|floated|current)\b",speech):
        return "drift"
    return "none"
