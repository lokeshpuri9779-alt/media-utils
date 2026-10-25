"""Story-specific CPU-animated human performances for The Tomorrow Signal.

This is a bounded, original 2D character performance, not generic clipart,
real-person imagery, neural video, or proof of general-purpose human animation.
Unknown actors/actions are rejected rather than falling back to a signal icon.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

from astra_errors import CreativeReject

PILOT_ID = "rayvan-season-01-episode-01"
EPISODE_TWO_ID = "rayvan-season-01-episode-02"
EPISODE_THREE_ID = "rayvan-season-01-episode-03"
ACTIONS = (
    "discover_radio",
    "trace_cable",
    "hear_warning",
    "flee_door",
)
EPISODE_TWO_ACTIONS = (
    "guard_knocking_door",
    "inspect_generator_clue",
    "inspect_future_photograph",
    "stop_stranger_switch",
)
EPISODE_THREE_ACTIONS = (
    "survey_dead_city",
    "inspect_reverse_clock",
    "study_altered_photographs",
    "confront_mara_double",
)
EPISODE_ACTIONS = {
    PILOT_ID: ACTIONS,
    EPISODE_TWO_ID: EPISODE_TWO_ACTIONS,
    EPISODE_THREE_ID: EPISODE_THREE_ACTIONS,
}
INK = (24, 34, 49)
SKIN = (198, 142, 111)
HAIR = (42, 37, 51)
JACKET = (51, 121, 139)
PANTS = (42, 55, 79)
RADIO = (62, 73, 93)
GOLD = (249, 190, 92)


def validate_human_scene(shot):
    """Permit only explicitly storyboarded actions in two known serialized episodes."""
    story_id = shot.get("story_visual_seed")
    allowed = EPISODE_ACTIONS.get(story_id)
    if allowed is None:
        raise CreativeReject("Human performer not approved for this story identity")
    if shot.get("story_human_actor") != "mara":
        raise CreativeReject("Unknown human actor; no procedural fallback")
    action = shot.get("story_human_action")
    if action not in allowed:
        raise CreativeReject("Unrenderable human action for this episode: " + str(action))
    if shot.get("story_cast"):
        raise CreativeReject("Human episode does not support an animal cast")
    narration = str(shot.get("speech") or "").lower()
    if not narration.strip():
        raise CreativeReject("Missing narrated human action")
    if story_id == PILOT_ID:
        if action in ("discover_radio", "trace_cable") and "radio" not in narration:
            raise CreativeReject("Radio action lacks a narrated radio")
        if action == "hear_warning" and not any(word in narration for word in ("voice", "countdown", "blackout")):
            raise CreativeReject("Warning scene lacks a narrated warning")
        if action == "flee_door" and not any(word in narration for word in ("door", "stairs")):
            raise CreativeReject("Escape scene has no door or stairs")
        expected = "signal" if action in ("discover_radio", "trace_cable") else "door"
    elif story_id == EPISODE_TWO_ID:
        required_terms = {
            "guard_knocking_door": ("knocked", "door"),
            "inspect_generator_clue": ("generator", "notebook"),
            "inspect_future_photograph": ("photograph", "stranger", "key"),
            "stop_stranger_switch": ("stranger", "switch", "lights"),
        }
        if not all(term in narration for term in required_terms[action]):
            raise CreativeReject("Episode 2 actor action does not match narrated event")
        expected = "door"
    else:
        required_terms = {
            "survey_dead_city": ("city", "door", "footprints"),
            "inspect_reverse_clock": ("clock", "threshold", "radio"),
            "study_altered_photographs": ("jacket", "photographs", "stranger"),
            "confront_mara_double": ("another mara", "key", "radios"),
        }
        if not all(term in narration for term in required_terms[action]):
            raise CreativeReject("Episode 3 actor action does not match narrated event")
        expected = "door"
    if str(shot.get("visual") or "").lower() != expected:
        raise CreativeReject("Human action requires authored " + expected + " visual")
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


def _generator(draw, t):
    """Stationary emergency generator; toggling switch is a separate later event."""
    draw.rounded_rectangle((650,945,973,1159),radius=25,
                           fill=(81,91,103),outline=(204,181,130),width=9)
    draw.rectangle((710,986,891,1046),fill=(20,37,54),outline=(119,167,179),width=5)
    for k in range(5):
        x=729+k*30
        draw.line(((x,999),(x,1035)),fill=(77,204,191),width=5)
    draw.ellipse((711,1103,752,1141),fill=(193,164,114))
    draw.ellipse((858,1103,899,1141),fill=(193,164,114))
    draw.line(((918,971),(935,925)),fill=(205,201,191),width=12)
    draw.ellipse((924,914,946,936),fill=(238,190,92))


def _notebook(draw, t):
    """Close foreground notebook, carrying the repeated mark."""
    x=280+int(4*math.sin(t*2.3))
    y=1080
    draw.polygon(((x,y),(x+230,y-14),(x+248,y+106),(x+10,y+128)),
                 fill=(188,161,118),outline=INK,width=7)
    draw.polygon(((x+20,y+15),(x+218,y+2),(x+230,y+85),(x+30,y+105)),
                 fill=(230,222,194))
    # Shared glyph from the generator switch, a diamond with a divider.
    draw.polygon(((x+125,y+32),(x+151,y+59),(x+125,y+86),(x+99,y+59)),
                 outline=(65,109,131),width=6)
    _line(draw,((x+102,y+60),(x+148,y+60)),(65,109,131),4)


def _stranger(draw, x, y, t, *, touching_switch=False):
    """Distinct stranger silhouette; do not invent the missing brother's appearance."""
    bob=int(5*math.sin(t*1.9))
    y+=bob
    draw.ellipse((x-77,y-208,x+77,y-66),fill=(85,86,114),outline=INK,width=7)
    draw.ellipse((x-62,y-179,x+62,y-83),fill=(68,63,89))
    draw.polygon(((x-77,y-79),(x+75,y-79),(x+107,y+226),(x-110,y+226)),
                 fill=(93,75,114),outline=INK,width=8)
    draw.polygon(((x-81,y-95),(x+81,y-95),(x+59,y-235),(x-62,y-235)),
                 fill=(48,44,69),outline=INK,width=5)
    _line(draw,((x-74,y-40),(x-131,y+155)),(93,75,114),35)
    hand=(x+156,y-3) if touching_switch else (x+125,y+112)
    _line(draw,((x+73,y-38),hand),(93,75,114),34)
    draw.ellipse((hand[0]-15,hand[1]-15,hand[0]+15,hand[1]+15),
                 fill=(159,121,118),outline=INK,width=3)
    _line(draw,((x-43,y+215),(x-59,y+346)),PANTS,35)
    _line(draw,((x+42,y+215),(x+64,y+346)),PANTS,35)


def _future_photograph(draw):
    """The future, Mara and her brother are depicted only *inside* a dated photo."""
    draw.rounded_rectangle((530,780,944,1130),radius=14,
                           fill=(219,212,191),outline=INK,width=10)
    draw.rectangle((563,816,914,1067),fill=(86,113,131))
    # Silhouettes within the picture, not extra live actors.
    for x,shade in ((650,(63,57,69)),(807,(86,73,94))):
        draw.ellipse((x-33,855,x+33,921),fill=shade)
        draw.polygon(((x-53,916),(x+53,916),(x+69,1025),(x-67,1025)),fill=shade)
    draw.polygon(((749,937),(765,920),(781,937),(765,957)),
                 fill=(72,171,230),outline=(208,239,255),width=4)
    draw.rectangle((626,1080,852,1094),fill=(119,102,97))


def _city_power(draw, t):
    """Exterior lighting progressively returns while the stranger flips a switch."""
    for j in range(6):
        x=108+j*133
        height=110+(j%3)*42
        draw.rectangle((x,1015-height,x+84,1015),fill=(44,58,78))
        for k in range(2):
            for m in range(3):
                lit=t>=.55+j*.32
                col=(245,196,107) if lit else (40,47,63)
                draw.rectangle((x+15+k*34,1015-height+15+m*29,
                                x+27+k*34,1015-height+27+m*29),fill=col)


def _alternate_city(draw, t):
    """Vacant, starless skyline through the open observatory doorway."""
    draw.polygon(((680,695),(955,695),(981,1164),(667,1164)),
                 fill=(9,17,33),outline=(142,170,186),width=5)
    # Perspective city remains abandoned: dark windows, no living silhouettes.
    for index in range(5):
        x=683+index*52
        y=839-(index%3)*42
        draw.rectangle((x,y,x+44,1137),fill=(38,59,77))
        for j in range(3):
            draw.rectangle((x+8,y+23+j*40,x+19,y+38+j*40),fill=(13,24,41))
    # Floor footprints advance toward the camera in alternating steps.
    for i in range(4):
        x=715+(i%2)*58+int(6*math.sin(t*.8))
        y=1028+i*44
        draw.ellipse((x,y,x+28,y+16),fill=(144,150,154))


def _reverse_clock(draw,t):
    """Clock's single moving hand unmistakably runs counter-clockwise."""
    x,y,r=748,876,154
    draw.ellipse((x-r,y-r,x+r,y+r),fill=(216,208,176),outline=INK,width=11)
    for hour in range(12):
        a=hour*math.tau/12-math.pi/2
        _line(draw,((int(x+126*math.cos(a)),int(y+126*math.sin(a))),
                    (int(x+141*math.cos(a)),int(y+141*math.sin(a)))),INK,6)
    angle=-math.pi/2-t*.95
    _line(draw,((x,y),(int(x+104*math.cos(angle)),int(y+104*math.sin(angle)))),INK,12)
    _line(draw,((x,y),(int(x+65*math.cos(angle*.35)),int(y+65*math.sin(angle*.35)))),(89,110,119),8)
    draw.ellipse((x-11,y-11,x+11,y+11),fill=INK)
    # Physical radio provides the second narrated story object.
    _radio(draw,736,1113,t,portable=True)


def _photo_wall(draw,t):
    """Readable photographic montage; the same Mara appears in divergent outcomes."""
    for col in range(3):
        x=615+col*109
        y=686+(col%2)*42
        draw.rounded_rectangle((x,y,x+92,y+165),radius=5,
                               fill=(222,212,188),outline=INK,width=5)
        draw.rectangle((x+12,y+12,x+80,y+133),fill=(91+col*7,106,123))
        draw.ellipse((x+28,y+39,x+65,y+83),fill=SKIN)
        draw.polygon(((x+22,y+82),(x+70,y+82),(x+79,y+124),(x+13,y+124)),
                     fill=JACKET if col!=1 else (132,90,104))
    # Brother's abandoned jacket and changed label beside the photographs.
    draw.polygon(((707,1020),(746,992),(769,1013),(795,994),(841,1032),
                  (882,1124),(835,1141),(819,1093),(811,1191),
                  (712,1191),(704,1093),(680,1139),(645,1115)),
                 fill=(114,100,86),outline=INK,width=7)
    draw.rectangle((754,1045,806,1068),fill=(222,210,176),outline=INK,width=3)
    # Pinwheel marks imply alternate choices without false full-motion claims.
    q=4*math.sin(t*2)
    draw.line(((570,830+q),(593,849+q)),fill=GOLD,width=7)


def _blue_glass_key(draw,x,y):
    """Recurring unique blue-glass prop, recognizable across this episode."""
    color=(72,171,233)
    draw.ellipse((x-28,y-26,x+27,y+26),fill=(42,108,178),outline=(198,236,255),width=7)
    draw.ellipse((x-11,y-10,x+10,y+11),fill=(17,48,94))
    _line(draw,((x+7,y+16),(x+8,y+108)),color,16)
    _line(draw,((x+8,y+78),(x+40,y+78)),color,12)
    _line(draw,((x+8,y+103),(x+31,y+103)),color,10)


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
    elif action == "guard_knocking_door":
        _door(d,.22+.045*math.sin(t*3.2))
        # An actual physical knock: repeated displacement at the door panel.
        for phase in range(3):
            x=886+phase*12
            radius=9+phase*10+int(abs(math.sin(t*3.2))*8)
            d.arc((x-radius,872-radius,x+radius,872+radius),
                  -85,85,fill=(130,187,222),width=4)
        _radio(d,350,1111,t,portable=True)
        _mara(d,368,857,t,alarm=True)
    elif action == "inspect_generator_clue":
        _generator(d,t)
        _notebook(d,t)
        _mara(d,375,865,t,reaching=True)
    elif action == "inspect_future_photograph":
        _future_photograph(d)
        _stranger(d,795,770,t)
        _mara(d,327,875,t,reaching=True,alarm=True)
    elif action == "stop_stranger_switch":
        _city_power(d,t)
        _door(d,min(.9,.25+max(0,t-.9)*.1))
        # The stranger actuates a dedicated wall switch; Mara reacts, not assists.
        d.rounded_rectangle((797,724,888,830),radius=12,
                            fill=(117,130,143),outline=INK,width=6)
        d.line(((838,771),(838,738 if t>1.1 else 804)),
               fill=(248,191,103),width=11)
        _stranger(d,675,856,t,touching_switch=True)
        _mara(d,279,870,t,reaching=True,alarm=True)
    elif action == "survey_dead_city":
        _door(d,.82)
        _alternate_city(d,t)
        _mara(d,337,864,t,reaching=True,alarm=True)
    elif action == "inspect_reverse_clock":
        _door(d,.42)
        _reverse_clock(d,t)
        _mara(d,346,865,t,reaching=True,alarm=True)
    elif action == "study_altered_photographs":
        _photo_wall(d,t)
        _mara(d,343,868,t,reaching=True,alarm=True)
    elif action == "confront_mara_double":
        _door(d,.73)
        # An independently moving matching human puppet, not a stranger/animal.
        # The double wears Mara's same palette and silhouette for continuity.
        _mara(d,307,865,t,reaching=True,alarm=True)
        _mara(d,748+int(10*math.sin(t*.85)),865,t,reaching=True,alarm=True)
        _blue_glass_key(d,866,969+int(6*math.sin(t*1.6)))
        _radio(d,255,1131,t,portable=True)
        _radio(d,865,1131,t,portable=True)
    else:
        raise CreativeReject("Unknown human action")
    return True
