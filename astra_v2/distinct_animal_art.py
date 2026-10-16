"""True-to-species Pillow silhouettes for ASTRA's previously mislabeled animals.

These designs are procedural CPU art. No third-party downloads, wrong-species
aliases, AI image provider, or pretrained GPU model is required.
"""
import math
from PIL import ImageDraw
from astra_v2.story_action_motion import offset
from astra_v2.motion_curves import limb_pose

SPECIES = ("beaver", "mole", "penguin", "heron")
INK = (35, 45, 56)
CREAM = (252, 235, 209)


def _blink(t, phase):
    return abs(math.sin(t*1.65 + phase)) > .988


def _eyes(draw, x, y, half_sep, t, phase, *, pupil=True, size=12):
    for side in (-1,1):
        ex=x+side*half_sep
        if _blink(t,phase):
            draw.line((ex-size,y,ex+size,y),fill=INK,width=6)
        else:
            draw.ellipse((ex-size-4,y-size-7,ex+size+4,y+size+7),
                         fill=(253,250,241),outline=INK,width=3)
            if pupil:
                draw.ellipse((ex-5,y-2,ex+7,y+11),fill=INK)
                draw.ellipse((ex-2,y+1,ex+1,y+4),fill=(255,255,255))


def _feet(draw, x, y, color, t, action):
    pose=limb_pose(action,t)
    for side in (-1,1):
        shift=pose["left_foot_x"] if side<0 else pose["right_foot_x"]
        legx=x+side*76
        draw.line((legx,y+235,legx+shift,y+326),fill=color,width=35)
        draw.ellipse((legx+shift-41,y+312,legx+shift+41,y+336),fill=color)


def draw_distinct_animal(image, subject, t, accent=(130,180,210), action="idle"):
    """Render a distinct focal character, avoiding generic icon fallbacks."""
    if subject not in SPECIES:
        return False
    d=ImageDraw.Draw(image)
    dx,dy=offset(action,t)
    cx=515+dx+int(15*math.sin(t*1.4))
    cy=795+dy+int(8*math.sin(t*1.9))
    blink_phase=len(subject)*.27
    gesture=math.sin(t*4.2)
    if subject=="beaver":
        brown=(149,97,66); lighter=(207,162,112)
        tail=int(25*math.sin(t*2))
        # Wide paddle tail with distinctive criss-cross texture.
        d.ellipse((cx+116,cy+88+tail,cx+335,cy+263+tail),
                  fill=(94,66,52),outline=INK,width=6)
        for n in range(4):
            xx=cx+168+n*32
            d.line((xx,cy+117+tail,xx+45,cy+235+tail),
                   fill=(141,100,73),width=4)
        d.ellipse((cx-153,cy-44,cx+156,cy+285),fill=brown,outline=INK,width=6)
        _feet(d,cx,cy,brown,t,action)
        for side in (-1,1):
            a=cx+side*123
            lift=int(75*abs(gesture)) if action in ("wave","carry","repair","pick") and side==1 else 0
            d.line((a,cy+92,a+side*45,cy+165-lift),fill=brown,width=37)
            d.ellipse((a+side*45-19,cy+150-lift,a+side*45+19,cy+176-lift),
                      fill=lighter)
        d.ellipse((cx-137,cy-230,cx+137,cy+58),fill=brown,outline=INK,width=6)
        for side in (-1,1):
            ex=cx+side*101
            d.ellipse((ex-30,cy-222,ex+30,cy-151),fill=brown,outline=INK,width=4)
        _eyes(d,cx,cy-142,54,t,blink_phase,size=13)
        d.ellipse((cx-88,cy-54,cx+90,cy+50),fill=lighter)
        d.ellipse((cx-20,cy-63,cx+20,cy-34),fill=INK)
        for side in (-1,1):
            bx=cx+side*27
            d.rounded_rectangle((bx-19,cy-8,bx+19,cy+57),radius=7,
                                fill=(252,249,230),outline=INK,width=3)
        d.arc((cx-58,cy-13,cx+58,cy+74),10,170,fill=INK,width=5)

    elif subject=="mole":
        fur=(115,112,126); belly=(155,149,152); pink=(232,157,175)
        d.ellipse((cx-168,cy-64,cx+168,cy+277),fill=fur,outline=INK,width=6)
        _feet(d,cx,cy,(105,95,104),t,action)
        for side in (-1,1):
            sx=cx+side*140
            lift=int(60*abs(gesture)) if action in ("repair","pick","run","wave") else 0
            d.line((sx,cy+80,sx+side*92,cy+141-lift),fill=fur,width=54)
            d.ellipse((sx+side*92-49,cy+107-lift,sx+side*92+49,cy+177-lift),
                      fill=pink,outline=INK,width=5)
            for j in range(3):
                clawx=sx+side*(112+j*10)
                d.line((clawx,cy+139-lift,clawx+side*22,cy+160-lift),
                       fill=CREAM,width=7)
        d.ellipse((cx-175,cy-230,cx+175,cy+94),fill=fur,outline=INK,width=6)
        d.ellipse((cx-120,cy-95,cx+120,cy+102),fill=belly)
        _eyes(d,cx,cy-144,70,t,blink_phase,pupil=True,size=8)
        d.ellipse((cx-37,cy-63,cx+37,cy-9),fill=pink,outline=INK,width=4)
        for side in (-1,1):
            for j in range(3):
                d.line((cx+side*27,cy-30+j*15,
                        cx+side*(145+j*7),cy-42+j*31),
                       fill=(210,200,190),width=4)

    elif subject=="penguin":
        navy=(42,62,78); snow=(251,245,227); beak=(241,161,82)
        _feet(d,cx,cy,(220,140,79),t,action)
        d.ellipse((cx-151,cy-162,cx+151,cy+290),fill=navy,outline=INK,width=6)
        d.ellipse((cx-108,cy-82,cx+108,cy+237),fill=snow)
        for side in (-1,1):
            ax=cx+side*131
            flap=int(83*math.sin(t*5.7+side)) if action in ("run","jump","wave","dance") else int(16*math.sin(t*1.5+side))
            d.polygon([(ax,cy-40),(ax+side*87,cy+125-flap),
                       (ax+side*62,cy+181-flap),(ax-side*7,cy+85)],
                      fill=navy,outline=INK,width=5)
        d.ellipse((cx-135,cy-248,cx+135,cy+16),fill=navy,outline=INK,width=6)
        for side in (-1,1):
            ex=cx+side*54
            d.ellipse((ex-39,cy-196,ex+39,cy-88),fill=snow)
        _eyes(d,cx,cy-139,55,t,blink_phase,size=15)
        d.polygon([(cx-44,cy-60),(cx+44,cy-60),(cx+7,cy-1)],fill=beak)
        d.arc((cx-51,cy-18,cx+51,cy+62),5,175,fill=INK,width=5)
        # Scarf makes the subject readable on dark mobile backgrounds.
        d.arc((cx-113,cy-49,cx+116,cy+87),20,160,fill=(185,91,92),width=21)
        d.line((cx+60,cy+49,cx+99,cy+161),fill=(185,91,92),width=25)

    else: # heron — long curved neck, slender beak, extended legs, gray wings
        feathers=(126,161,170); wing=(84,130,146)
        _feet(d,cx,cy,(184,110,88),t,action)
        d.ellipse((cx-165,cy+36,cx+150,cy+242),fill=feathers,outline=INK,width=6)
        wing_angle=int(75*math.sin(t*5)) if action in ("run","jump","wave") else int(13*math.sin(t*1.3))
        d.polygon([(cx-85,cy+90),(cx-260,cy-30-wing_angle),
                   (cx-175,cy+219),(cx+18,cy+186)],fill=wing,outline=INK,width=5)
        d.polygon([(cx+85,cy+90),(cx+228,cy+36+wing_angle),
                   (cx+174,cy+205),(cx-20,cy+186)],fill=wing,outline=INK,width=5)
        # Neck doubles back toward a recognizable profile and pointed beak.
        d.line([(cx+70,cy+95),(cx+35,cy+20),(cx-12,cy-86),
                (cx+36,cy-190)],fill=feathers,width=52,joint="curve")
        d.ellipse((cx-34,cy-256,cx+117,cy-127),fill=feathers,outline=INK,width=5)
        d.polygon([(cx+98,cy-210),(cx+271,cy-182),
                   (cx+106,cy-163)],fill=(241,161,82),outline=INK,width=4)
        d.ellipse((cx+45,cy-218,cx+70,cy-192),fill=INK)
        d.ellipse((cx+50,cy-212,cx+58,cy-204),fill=(255,255,255))
        for i in range(3):
            d.line((cx-72+i*12,cy-241,cx-82+i*18,cy-277),
                   fill=INK,width=5)
    return True
