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
    "garden","workshop","market","station","home","forest",
    "bakery","greenhouse","observatory","cave","school","lighthouse",
    "theater","harbor",
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
    "garden":((97,150,147),(74,122,91),(180,204,148)),
    "workshop":((88,111,124),(101,88,78),(198,165,116)),
    "market":((122,147,151),(120,111,99),(221,181,133)),
    "station":((101,131,143),(106,109,122),(192,179,157)),
    "home":((112,137,151),(125,107,105),(210,179,145)),
    "forest":((66,122,121),(60,111,92),(152,181,123)),
    "bakery":((115,127,136),(156,115,98),(232,183,129)),
    "greenhouse":((90,143,154),(80,133,101),(184,216,169)),
    "observatory":((48,86,123),(70,92,122),(193,213,226)),
    "cave":((61,80,89),(70,75,72),(144,160,144)),
    "school":((126,146,164),(139,118,108),(220,192,142)),
    "lighthouse":((86,147,169),(57,114,142),(225,213,173)),
    "theater":((105,76,114),(137,78,95),(225,191,136)),
    "harbor":((90,143,166),(78,123,139),(213,195,152)),
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
            # A real low timber crossing, not the old bright scene-spanning
            # suspension curve that resembled a renderer guide arc.
            d.rectangle((116,1002,935,1042),fill=(150,105,78))
            for x in range(154,933,92):
                d.rectangle((x,958,x+14,1030),fill=(123,96,83))
                d.ellipse((x+3,967,x+11,975),fill=(192,170,141))
            _line(d,((124,961),(931,961)),(130,111,94),8)
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
    elif name in ("garden","forest"):
        # Real foreground/midground plants with fixed identities per scene.
        for row in range(2):
            for k in range(5):
                x=105+k*210+(row%2)*24
                top=720+row*185+(k%2)*29
                if name=="forest":
                    d.rectangle((x+37,top+63,x+66,1120),fill=(104,81,69))
                    d.polygon(((x-42,top+130),(x+49,top-80),
                               (x+132,top+130)),fill=(48+row*12,112+row*6,87))
                    d.polygon(((x-26,top+38),(x+49,top-125),
                               (x+113,top+38)),fill=(59+row*8,132,97))
                else:
                    d.rounded_rectangle((x-19,top+94,x+104,top+151),radius=8,
                                        fill=(132,96,80))
                    for j in range(3):
                        px=x+j*36
                        d.line((px,top+106,px,top+32),fill=(65,139,87),width=6)
                        d.ellipse((px-15,top+11,px+15,top+41),
                                  fill=((220,152,151) if j%2 else (234,198,105)))
    elif name=="workshop":
        for x in (115,750):
            d.rectangle((x,600,x+210,1020),fill=(101,88,83),outline=highlight,width=7)
            for y in (697,845,974):
                d.rectangle((x+10,y,x+199,y+15),fill=(157,133,105))
            for k in range(6):
                px=x+24+(k%3)*61;py=632+(k//3)*159
                d.rectangle((px,py,px+28,py+53),fill=(128+k*11,145,148))
        d.rounded_rectangle((327,990,740,1130),radius=10,fill=(137,98,77))
        for x in (396,660):
            d.rectangle((x,1110,x+25,1280),fill=(104,79,66))
    elif name=="market":
        for x,color in ((90,(194,114,94)),(390,(124,165,150)),(698,(211,166,102))):
            d.rectangle((x+20,760,x+235,1060),fill=(141,127,116))
            for stripe in range(5):
                d.polygon(((x+stripe*52,728),(x+(stripe+1)*52,728),
                           (x+(stripe+1)*52,800),(x+stripe*52,800)),
                          fill=color if stripe%2==0 else (237,218,183))
            d.rectangle((x+10,1027,x+260,1070),fill=(119,86,74))
    elif name=="station":
        for x in (122,648):
            d.rounded_rectangle((x,568,x+281,1040),radius=15,
                                fill=(86,105,117),outline=highlight,width=8)
            for k in range(3):
                y=626+k*125
                d.rectangle((x+20,y,x+260,y+85),fill=(157,199,205))
        d.rectangle((70,1030,1020,1075),fill=(141,131,114))
        d.line((110,1170,990,1170),fill=(174,176,170),width=12)
    elif name=="home":
        d.rectangle((115,577,971,1115),fill=(154,127,112))
        for x in (169,718):
            d.rounded_rectangle((x,652,x+193,924),radius=12,
                                fill=(119,166,176),outline=(222,199,151),width=12)
            d.line((x+96,660,x+96,916),fill=(222,199,151),width=8)
        d.rounded_rectangle((430,847,667,1118),radius=9,
                            fill=(101,87,82),outline=highlight,width=8)
        d.ellipse((605,978,623,995),fill=(235,208,138))
    elif name=="bakery":
        d.rectangle((118,600,968,1090),fill=(175,148,129))
        d.rectangle((140,626,946,664),fill=(114,88,78))
        for x in (166,726):
            d.rounded_rectangle((x,704,x+242,1001),radius=16,
                                fill=(96,93,88),outline=highlight,width=9)
            for yy in (790,884):
                d.rectangle((x+19,yy,x+222,yy+13),fill=(216,180,129))
        d.rounded_rectangle((388,983,694,1137),radius=16,
                            fill=(169,115,85),outline=highlight,width=7)
        for j in range(4):
            x=421+j*65
            d.ellipse((x-21,954,x+25,991),fill=(218,163,107))
            _line(d,((x-12,970),(x+12,970)),(169,112,81),3)
    elif name=="greenhouse":
        for j in range(4):
            x=95+j*255
            d.polygon(((x,1092),(x+15,619),(x+230,619),(x+240,1092)),
                      fill=(113,174,155),outline=highlight,width=7)
            d.rectangle((x+35,735,x+200,1045),fill=(98,143,127))
        for row in range(2):
            for j in range(7):
                x=105+j*137
                y=900+row*100
                d.line((x,y+130,x,y),fill=(65,132,89),width=7)
                d.ellipse((x-21,y-38,x+21,y+5),fill=(168,198,111))
    elif name=="observatory":
        d.polygon(((86,1020),(150,718),(394,624),(691,624),(916,718),
                   (983,1020)),fill=(83,119,143))
        d.ellipse((329,562,756,891),fill=(129,152,173),outline=highlight,width=12)
        d.rectangle((340,729,745,1099),fill=(69,89,118))
        d.polygon(((447,652),(716,650),(728,679),(460,702)),
                  fill=(194,199,196))
        d.ellipse((683,625,783,717),fill=(53,74,100),outline=highlight,width=7)
        for i in range(12):
            x=132+(i*173)%816
            y=551+(i*73)%150
            d.ellipse((x,y,x+5,y+5),fill=(220,225,217))
    elif name=="cave":
        d.polygon(((55,600),(185,537),(309,681),(479,573),(668,681),
                   (831,523),(1025,609),(1025,1110),(55,1110)),
                  fill=(99,102,96))
        for j in range(8):
            x=80+j*121
            h=84+(j%3)*31
            d.polygon(((x,565),(x+55,565),(x+29,565+h)),
                      fill=(68,82,84))
        d.ellipse((230,829,851,1169),fill=(43,62,75),outline=(128,135,128),width=12)
        for j in range(4):
            x=155+j*211
            d.polygon(((x,1130),(x+54,982),(x+104,1130)),
                      fill=(152,146,130))
    elif name=="school":
        d.rectangle((109,589,971,1090),fill=(153,139,132))
        d.rounded_rectangle((273,614,797,857),radius=18,
                            fill=(49,91,88),outline=(219,189,131),width=10)
        for j in range(4):
            x=135+j*226
            d.rounded_rectangle((x,943,x+165,1087),radius=13,
                                fill=(135,95,76),outline=(202,168,125),width=5)
            d.rectangle((x+22,1076,x+39,1148),fill=(91,75,63))
            d.rectangle((x+133,1076,x+150,1148),fill=(91,75,63))
    elif name=="lighthouse":
        d.polygon(((55,1088),(317,1028),(597,1098),(1025,1027),
                   (1025,1165),(55,1165)),fill=(73,130,142))
        d.polygon(((404,1065),(464,615),(610,615),(670,1065)),
                  fill=(223,209,184),outline=(104,115,117),width=7)
        d.polygon(((466,616),(494,536),(580,536),(610,616)),fill=(142,89,88))
        d.rectangle((488,580,586,630),fill=(239,213,135))
        for j in range(4):
            x=130+j*247
            y=1112+(j%2)*22
            _line(d,((x,y),(x+130,y+12)),(163,205,217),5)
    elif name=="theater":
        d.rectangle((83,561,1005,1097),fill=(67,57,88))
        for x,flipped in ((105,1),(805,-1)):
            d.polygon(((x,576),(x+flipped*147,576),
                       (x+flipped*108,1090),(x,1090)),
                      fill=(167,69,93))
        d.rectangle((192,1030,887,1121),fill=(139,96,79))
        for j in range(4):
            x=233+j*190
            d.ellipse((x-26,591,x+26,632),fill=(232,197,135))
            d.line((x,630,x,669),fill=(224,190,134),width=9)
    elif name=="harbor":
        d.polygon(((55,824),(305,734),(535,835),(805,723),
                   (1025,816),(1025,1100),(55,1100)),fill=(92,152,160))
        for j in range(4):
            y=1017+j*33
            _line(d,((60,y),(1022,y+11)),(127+j*6,190,195),5)
        d.rectangle((150,963,886,1013),fill=(155,119,91))
        for x in range(178,880,155):
            d.rectangle((x,982,x+22,1206),fill=(105,86,75))
        d.polygon(((587,925),(656,844),(735,924)),fill=(221,199,148))
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
    # Foreground activity is conditional on the spoken event; it is not a
    # random decorative overlay that could flash at every shot boundary.
    if environment in ("river","bridge") and re.search(r"\b(?:boat|ferry|raft)\b",text):
        water_bob=int(3*math.sin(t*1.2))
        d.polygon(((535,1000+water_bob),(770,1000+water_bob),
                   (732,1034+water_bob),(572,1034+water_bob)),
                  fill=(147,104,79),outline=(67,76,84))
        d.line((644,992+water_bob,644,906+water_bob),fill=(91,78,72),width=8)
        d.polygon(((649,911+water_bob),(649,973+water_bob),
                   (713,974+water_bob)),fill=(230,216,177))
    if environment in ("bridge","tunnel") and re.search(r"\b(?:bolt|counterweight|rope|pulley)\b",text):
        d.rounded_rectangle((840,905,891,943),radius=7,
                            fill=(121,137,143),outline=(52,62,71),width=6)
        for yy in (940,967,994):
            d.rectangle((858,yy,872,yy+14),fill=(189,186,156))
    if environment=="concert_hall" and re.search(r"\b(?:score|music|note|orchestra)\b",text):
        d.polygon(((490,920),(640,920),(656,1001),(475,1001)),
                  fill=(225,211,182),outline=(76,67,79))
        for yy in (945,957,969,981):
            d.line((505,yy,628,yy),fill=(101,95,105),width=2)
        d.line((560,1001,560,1096),fill=(107,86,78),width=10)
    if environment in ("hills","street","bridge","garden","forest","market"):
        # A moving but predictable set of foreground plants and small stones
        # adds depth without spawning extra animals or flickering props.
        for k in range(7):
            x=105+k*140
            y=1208+(k%3)*25
            d.arc((x-16,y-17,x+16,y+17),180,340,fill=(95,159,127),width=5)
            if k%2==0:
                d.ellipse((x+16,y+8,x+36,y+20),fill=(145,153,147))

