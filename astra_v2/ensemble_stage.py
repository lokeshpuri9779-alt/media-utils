"""Story-specific backdrops for ensemble fiction; all drawing inside safe zone.

Original Pillow vector sets. No external assets, no human likenesses and no
fake stock footage. This is separate from the standard Studio 7.3 backgrounds.
"""
from __future__ import annotations
import math
from PIL import ImageDraw

ENVIRONMENTS=frozenset((
    "courtroom","clocktower","river","library","attic","auction",
    "street","concert_hall","bridge","tunnel","hills","museum","gallery",
))
BOUNDS=(55,485,1025,1370)
PALETTES={
    "courtroom":((58,77,104),(101,87,90),(178,143,108)),
    "clocktower":((53,91,112),(60,96,107),(218,183,124)),
    "river":((54,107,132),(52,91,105),(107,157,167)),
    "library":((75,92,114),(107,81,77),(193,156,114)),
    "attic":((78,96,120),(99,87,76),(167,155,133)),
    "auction":((98,64,102),(130,74,90),(224,178,106)),
    "street":((73,124,131),(86,121,114),(202,157,107)),
    "concert_hall":((77,61,110),(128,68,95),(227,181,113)),
    "bridge":((69,139,153),(83,132,141),(216,190,152)),
    "tunnel":((52,77,84),(98,94,91),(195,153,108)),
    "hills":((87,136,150),(88,136,124),(220,194,130)),
    "museum":((87,99,125),(126,116,111),(193,172,132)),
    "gallery":((55,96,122),(74,114,121),(217,179,111)),
}

def _line(d,points,color,width=6):
    d.line(points,fill=color,width=width,joint="curve")

def draw_ensemble_stage(d, environment, t, shot=None):
    """Draw story-grounded sets inside the safe region, with no global arcs."""
    name=environment if environment in ENVIRONMENTS else "hills"
    sky,wall,highlight=PALETTES[name]
    d.rectangle((55,485,1025,1370),fill=sky)
    d.rectangle((55,1095,1025,1370),fill=wall)
    # Shared floor grounding with perspective to avoid floating sprites.
    for k in range(4):
        y=1132+k*59
        _line(d,((55,y),(1025,y)),tuple(max(0,v-10-k*5) for v in wall),3)
    if name=="courtroom":
        d.rectangle((80,535,1000,1115),fill=(75,80,93),outline=highlight,width=8)
        for x in (180,850):
            d.rounded_rectangle((x,565,x+85,1070),radius=12,
                                fill=(113,108,99),outline=highlight,width=5)
        d.ellipse((422,552,670,792),fill=(66,88,111),outline=highlight,width=9)
        _line(d,((546,582),(546,757)),highlight,7)
        _line(d,((492,654),(598,654)),highlight,6)
        d.rounded_rectangle((343,930,747,1133),radius=9,
                            fill=(128,85,72),outline=highlight,width=9)
    elif name=="clocktower":
        for x in (110,795):
            d.rectangle((x,580,x+180,1130),fill=(78,95,111),
                        outline=highlight,width=7)
        d.ellipse((381,570,698,888),fill=(217,205,169),outline=(81,87,96),width=14)
        d.ellipse((410,600,669,860),outline=(97,105,110),width=5)
        for i in range(12):
            a=i*math.pi/6
            x=540+math.sin(a)*110;y=730-math.cos(a)*110
            d.ellipse((x-4,y-4,x+4,y+4),fill=(75,85,92))
        _line(d,((540,730),(540,643)),(67,75,88),10)
        _line(d,((540,730),(605,760)),(67,75,88),8)
    elif name in ("river","bridge"):
        d.polygon(((55,775),(335,595),(540,742),(804,560),
                   (1025,743),(1025,1170),(55,1170)),fill=(67,110,122))
        for k in range(4):
            y=996+k*65+int(4*math.sin(t+k))
            d.polygon(((55,y),(220,y-13),(420,y+7),(620,y-6),
                       (842,y+12),(1025,y-14),(1025,y+49),(55,y+49)),
                      fill=(49+k*5,119+k*3,145+k*3))
        if name=="bridge":
            for x in (105,920):
                d.rectangle((x,580,x+22,1050),fill=(183,145,111))
            _line(d,((115,620),(540,894),(932,620)),highlight,9)
            _line(d,((115,1025),(932,1025)),(190,151,109),18)
            for x in range(195,925,95):
                top=620+abs(525-x)*.5
                _line(d,((x,top),(x,1025)),(201,167,132),5)
    elif name in ("library","attic"):
        for x in (100,660):
            d.rounded_rectangle((x,565,x+320,1120),radius=10,
                                fill=(98,78,89),outline=highlight,width=8)
            for row in range(4):
                y=610+row*126
                d.rectangle((x+11,y+75,x+311,y+86),fill=highlight)
                for col in range(10):
                    bx=x+16+col*28
                    colors=((194,124,111),(131,160,157),(179,156,99),
                            (132,135,190))
                    d.rectangle((bx,y+9,bx+19,y+75),fill=colors[(row+col)%4])
        if name=="attic":
            d.polygon(((55,660),(540,485),(1025,660)),fill=(136,103,88))
            _line(d,((55,660),(540,485),(1025,660)),highlight,16)
    elif name in ("auction","street"):
        for x in (100,790):
            d.polygon(((x,710),(x+120,568),(x+225,710)),fill=(146,92,108))
            d.rectangle((x+20,710,x+205,1095),fill=(153,114,117))
            d.rounded_rectangle((x+64,778,x+172,921),radius=13,
                                fill=(213,186,145),outline=highlight,width=6)
        if name=="auction":
            d.rounded_rectangle((405,923,680,1140),radius=15,
                                fill=(130,85,84),outline=highlight,width=9)
            d.ellipse((477,855,609,986),outline=(229,192,115),width=11)
    elif name=="concert_hall":
        for side in (0,1):
            x=55 if side==0 else 820
            d.polygon(((x,485),(x+205,485),(x+169,1110),(x,1110)),
                      fill=(158,64,97),outline=(215,137,128),width=7)
        for y in (690,736,782,828):
            _line(d,((305,y),(773,y)),(224,187,142),3)
        d.rounded_rectangle((405,928,683,1124),radius=15,
                            fill=(119,92,122),outline=highlight,width=7)
        for x in (440,555,673):
            d.ellipse((x-12,858,x+12,894),fill=(238,210,147))
            _line(d,((x,892),(x,955)),highlight,5)
    elif name in ("museum","gallery"):
        for x in (115,710):
            d.rounded_rectangle((x,560,x+260,972),radius=7,
                                fill=(115,99,94),outline=highlight,width=14)
            d.rectangle((x+25,600,x+235,939),fill=(78,134,150))
            d.polygon(((x+25,870),(x+112,755),(x+161,832),
                       (x+235,718),(x+235,938),(x+25,938)),
                      fill=(141,162,136))
        d.ellipse((459,625,632,806),fill=(215,200,152),outline=(122,120,111),width=8)
        if name=="gallery":
            for k in range(4):
                y=1020+k*29+int(math.sin(t+k)*3)
                _line(d,((55,y),(1025,y+9)),(89,151,175),5)
    elif name=="tunnel":
        d.rounded_rectangle((128,540,951,1119),radius=250,
                            fill=(68,82,96),outline=(154,145,133),width=32)
        d.polygon(((320,1110),(457,710),(627,710),(785,1110)),
                  fill=(88,111,123))
        for k in range(5):
            y=790+k*70
            _line(d,((360-k*24,y),(726+k*24,y)),highlight,7)
    else: # hills
        for k in range(4):
            x=95+k*245
            d.polygon(((x-150,1050),(x+75,620+k%2*85),
                       (x+290,1050)),fill=(73+k*4,116+k*3,114+k*2))
        d.polygon(((140,1100),(460,845),(690,970),(950,790),
                   (1025,1185),(55,1185)),fill=(112,142,130))
    # Set dressing only when grounded in this beat's narration; no circular
    # director-guide lines or decorative golden trajectories may leak to film.
    _story_set_dressing(d, name, shot or {}, t, highlight)
    return name


def _story_set_dressing(d, environment, shot, t, accent):
    """Small story-specific set pieces; stable within each beat."""
    import re
    text=" ".join(str(shot.get(key) or "") for key in
                  ("speech","headline","visual_prompt")).lower()
    # Useful environmental detail: a physical clock on the wall, never
    # a floating motion guide. Clock hands move continuously across frames.
    if (re.search(r"\b(?:clock|timepiece|alarm)\b", text) and
            environment in ("courtroom","museum","clocktower","gallery","library")):
        cx,cy=855,646
        d.ellipse((cx-55,cy-55,cx+55,cy+55),fill=(235,221,183),
                  outline=(83,83,97),width=8)
        for k in range(12):
            angle=k*math.pi/6
            px=cx+43*math.sin(angle);py=cy-43*math.cos(angle)
            d.ellipse((px-3,py-3,px+3,py+3),fill=(75,75,89))
        d.line((cx,cy,cx+int(30*math.cos(t*.04)),cy-int(30*math.sin(t*.04))),
               fill=(63,72,84),width=5)
        d.line((cx,cy,cx-int(18*math.sin(t*.003)),
                cy-int(18*math.cos(t*.003))),fill=(63,72,84),width=7)
    if (re.search(r"\b(?:photograph|photo|picture|portrait)\b",text) and
            environment in ("museum","gallery","courtroom","attic")):
        d.rounded_rectangle((705,855,895,1000),radius=8,
                            fill=(222,207,175),outline=(105,86,82),width=8)
        d.polygon(((731,963),(779,917),(811,947),(850,901),
                   (875,966)),fill=(90,146,149))
        d.ellipse((754,881,780,907),fill=(214,173,104))
    if re.search(r"\b(?:storm|raining|rainfall|heavy rain)\b",text) and environment in ("river","bridge","hills","street"):
        for k in range(16):
            x=100+(k*61)%900
            y=565+(k*93)%490 + int(11*math.sin(t*1.5+k))
            d.line((x,y,x-8,y+24),fill=(141,187,199),width=3)
    if environment in ("hills","street","bridge"):
        # A moving but predictable set of foreground plants and small stones
        # adds depth without spawning extra animals or flickering props.
        for k in range(7):
            x=105+k*140
            y=1208+(k%3)*25
            d.arc((x-16,y-17,x+16,y+17),180,340,fill=(95,159,127),width=5)
            if k%2==0:
                d.ellipse((x+16,y+8,x+36,y+20),fill=(145,153,147))

