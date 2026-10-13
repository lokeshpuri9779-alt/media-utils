"""Experimental character/prop catalog with deterministic animation.

Catalog entries are procedurally differentiated designs, not hand-authored
characters. No paid API, downloads or production publishing.
"""
import math
from PIL import ImageDraw

SPECIES = ("human","robot","cat","dog","fox","rabbit","bear","owl","bird","frog",
           "turtle","fish","mouse","monkey","lion","penguin","deer","dragon","alien","ghost")
ROLES = ("explorer","chef","pilot","scientist","artist","farmer","detective","athlete","musician","builder")
STYLES = ("classic","tiny","tall","round","angular","soft","bright","dark","striped","spotted")
CHARACTER_COUNT = len(SPECIES)*len(ROLES)*len(STYLES)

OBJECTS = ("car","train","airplane","boat","rocket","bicycle","clock","book","lamp","chair",
           "table","door","key","chest","camera","phone","computer","umbrella","ball","guitar",
           "tree","flower","mushroom","house","castle","bridge","mountain","cloud","star","planet",
           "cup","bottle","apple","pizza","cake","hat","shoe","backpack","gift","telescope")
MATERIALS = ("wood","metal","glass","stone","paper","fabric","ceramic","plastic","gold","neon")
OBJECT_MOTIONS = ("bob","sway","spin","slide","pulse")
OBJECT_COUNT = len(OBJECTS)*len(MATERIALS)*len(OBJECT_MOTIONS)
assert CHARACTER_COUNT == 2000 and OBJECT_COUNT == 2000

def character(index):
    if not isinstance(index,int) or not 0<=index<CHARACTER_COUNT: raise ValueError(index)
    return SPECIES[index//100], ROLES[index//10%10], STYLES[index%10]

def prop(index):
    if not isinstance(index,int) or not 0<=index<OBJECT_COUNT: raise ValueError(index)
    return OBJECTS[index//50], MATERIALS[index//5%10], OBJECT_MOTIONS[index%5]

def draw_character(image,index,t,x=540,y=900,expression="neutral",gesture="idle"):
    species,role,style=character(index)
    d=ImageDraw.Draw(image)
    n=index%10
    base=(70+n*15,105+n*9,145+n*7)
    bob=int(14*math.sin(t*2.2))
    y+=bob
    width=95 if style=="tiny" else 150 if style=="round" else 120
    d.ellipse((x-width,y-185,x+width,y+80),fill=base)
    if species in ("cat","fox","rabbit","owl","bear","mouse"):
        ear=125 if species=="rabbit" else 75
        for side in (-1,1):
            d.polygon(((x+side*70,y-110),(x+side*80,y-190-ear),(x+side*25,y-160)),fill=base)
    elif species in ("robot","alien","ghost"):
        d.rounded_rectangle((x-100,y-160,x+100,y+55),radius=32,outline=(225,220,190),width=9)
    # Species-specific features; these are procedural cues, not hand-authored models.
    if species=="dog":
        for side in (-1,1):
            d.ellipse((x+side*105-32,y-125,x+side*105+32,y+15),fill=(114,80,63))
        d.ellipse((x-20,y+3,x+20,y+28),fill=(36,38,46))
    elif species=="fox":
        d.polygon(((x-50,y+2),(x,y+58),(x+50,y+2)),fill=(242,229,204))
    elif species=="owl":
        for dx in (-47,47):
            d.ellipse((x+dx-40,y-83,x+dx+40,y-5),fill=(237,224,196))
        d.polygon(((x-13,y-4),(x+13,y-4),(x,y+30)),fill=(238,173,71))
    elif species=="bird":
        d.polygon(((x-25,y+3),(x+95,y+22),(x-25,y+40)),fill=(236,176,75))
        d.polygon(((x-45,y-180),(x-15,y-255),(x+20,y-180)),fill=base)
    elif species=="frog":
        for dx in (-80,80):
            d.ellipse((x+dx-31,y-206,x+dx+31,y-144),fill=(102,190,111))
        d.ellipse((x-20,y+18,x+20,y+38),fill=(48,75,47))
    elif species=="turtle":
        d.ellipse((x-125,y+85,x+125,y+275),fill=(66,130,92),outline=(39,88,64),width=14)
        d.line((x-90,y+180,x+90,y+180),fill=(39,88,64),width=9)
    elif species=="fish":
        d.polygon(((x-90,y+50),(x-180,y-30),(x-180,y+130)),fill=base)
        d.polygon(((x-15,y-180),(x+45,y-260),(x+75,y-165)),fill=base)
    elif species=="monkey":
        for dx in (-112,112):
            d.ellipse((x+dx-45,y-90,x+dx+45,y+20),fill=(184,138,102))
        d.ellipse((x-55,y-20,x+55,y+70),fill=(214,177,139))
    elif species=="lion":
        d.ellipse((x-152,y-208,x+152,y+115),outline=(220,158,68),width=39)
    elif species=="penguin":
        d.ellipse((x-80,y+75,x+80,y+255),fill=(239,238,227))
        d.polygon(((x-22,y-3),(x+22,y-3),(x,y+32)),fill=(234,172,68))
    elif species=="deer":
        for side in (-1,1):
            d.line((x+side*60,y-140,x+side*105,y-270),fill=(134,99,66),width=13)
            d.line((x+side*86,y-216,x+side*140,y-244),fill=(134,99,66),width=10)
    elif species=="dragon":
        for dx in (-65,0,65):
            d.polygon(((x+dx-30,y-173),(x+dx,y-245),(x+dx+30,y-173)),fill=(108,191,154))
        d.polygon(((x-100,y+130),(x-205,y+40),(x-165,y+220)),fill=(108,191,154))
    elif species=="alien":
        for dx in (-55,55):
            d.ellipse((x+dx-30,y-70,x+dx+30,y-15),fill=(31,67,72))
        d.line((x,y-170,x,y-230),fill=base,width=12)
        d.ellipse((x-15,y-245,x+15,y-215),fill=(237,202,103))
    elif species=="robot":
        d.rectangle((x-80,y-150,x+80,y+40),outline=(65,82,97),width=13)
        d.line((x,y-175,x,y-225),fill=(160,170,182),width=9)
        d.ellipse((x-15,y-245,x+15,y-215),fill=(238,93,90))
    elif species=="ghost":
        d.arc((x-105,y-200,x+105,y+45),180,360,fill=(232,232,243),width=14)
        for dx in (-70,0,70):
            d.ellipse((x+dx-30,y+35,x+dx+30,y+100),fill=(229,229,240))
    elif species=="mouse":
        for dx in (-95,95):
            d.ellipse((x+dx-53,y-205,x+dx+53,y-99),fill=(221,170,175))
    elif species=="bear":
        d.ellipse((x-58,y+4,x+58,y+75),fill=(205,174,139))
    elif species=="rabbit":
        d.ellipse((x-15,y+5,x+15,y+32),fill=(226,165,168))
    elif species=="cat":
        d.line((x-25,y+10,x-120,y-4),fill=(38,45,55),width=5)
        d.line((x+25,y+10,x+120,y-4),fill=(38,45,55),width=5)
    if expression not in ("neutral", "surprised", "happy", "focused"):
        raise ValueError(f"unsupported facial expression: {expression}")
    for dx in (-48,48):
        if expression == "happy":
            d.arc((x+dx-17,y-55,x+dx+17,y-29),180,360,fill=(24,29,38),width=6)
        elif expression == "surprised":
            d.ellipse((x+dx-19,y-68,x+dx+19,y-25),fill=(24,29,38))
            d.ellipse((x+dx-8,y-61,x+dx+3,y-45),fill=(248,248,239))
        elif expression == "focused":
            d.ellipse((x+dx-13,y-60,x+dx+13,y-32),fill=(24,29,38))
            d.line((x+dx-22,y-70,x+dx+19,y-63),fill=(35,37,43),width=6)
        elif abs(math.sin(t*1.5))>.99:
            d.line((x+dx-14,y-45,x+dx+14,y-45),fill=(24,29,38),width=6)
        else:
            d.ellipse((x+dx-13,y-60,x+dx+13,y-32),fill=(24,29,38))
    if expression == "surprised":
        d.ellipse((x-15,y-12,x+15,y+23),fill=(35,37,43))
    elif expression == "focused":
        d.line((x-24,y+13,x+24,y+13),fill=(35,37,43),width=5)
    else:
        d.arc((x-32,y-20,x+32,y+28),0,180,fill=(35,37,43),width=5)
    d.ellipse((x-95,y+55,x+95,y+270),fill=base)
    if gesture not in ("idle", "point", "celebrate", "carry", "carry_rig"):
        raise ValueError(f"unsupported gesture: {gesture}")
    step=int(30*math.sin(t*4))
    for side in (-1,1):
        d.line((x+side*52,y+235,x+side*52+side*step,y+325),fill=base,width=27)
        if gesture == "celebrate":
            arm_end = (x+side*(110+int(12*math.sin(t*5))), y-100-int(15*math.sin(t*5)))
        elif gesture == "point" and side == 1:
            arm_end = (x+235, y+15)
        elif gesture == "carry":
            arm_end = (x+side*75, y+160)
        else:
            arm_end = (x+side*145, y+125+side*step)
        # The coordinated renderer supplies jointed, prop-attached arms for
        # carry_rig. Avoid drawing contradictory fixed arms underneath them.
        if gesture != "carry_rig":
            d.line((x+side*85,y+90,*arm_end),fill=base,width=19)
    # Visible occupation cues rather than the same badge for every role.
    gold=(248,217,136)
    if role=="chef":
        d.rectangle((x-60,y-240,x+60,y-183),fill=(244,241,226))
        for dx in (-43,0,43):
            d.ellipse((x+dx-35,y-285,x+dx+35,y-215),fill=(244,241,226))
    elif role=="pilot":
        d.polygon(((x-95,y-165),(x+95,y-165),(x+70,y-205),(x-70,y-205)),fill=(45,63,93))
        d.rectangle((x-65,y-202,x+65,y-184),fill=gold)
    elif role=="scientist":
        d.rectangle((x-77,y+85,x-37,y+230),fill=(236,235,225))
        d.rectangle((x+37,y+85,x+77,y+230),fill=(236,235,225))
        d.ellipse((x-19,y+118,x+19,y+154),outline=gold,width=6)
    elif role=="detective":
        d.polygon(((x-110,y-168),(x+110,y-168),(x+60,y-213),(x-60,y-213)),fill=(86,65,53))
        d.line((x-100,y-174,x+100,y-174),fill=gold,width=8)
    elif role=="musician":
        d.ellipse((x+90,y+100,x+155,y+190),outline=gold,width=10)
        d.line((x+155,y+100,x+155,y-25),fill=gold,width=8)
    elif role=="athlete":
        d.line((x-85,y+105,x+85,y+105),fill=gold,width=13)
        d.text((x-14,y+130),"1",fill=gold)
    elif role=="builder":
        d.arc((x-95,y-260,x+95,y-145),180,360,fill=gold,width=23)
        d.line((x-110,y-175,x+110,y-175),fill=gold,width=13)
    elif role=="artist":
        d.ellipse((x+95,y+100,x+165,y+155),outline=gold,width=9)
        for dx in (105,130,155):
            d.ellipse((x+dx,y+125,x+dx+10,y+135),fill=(240,130,140))
    elif role=="farmer":
        d.line((x-110,y-185,x+110,y-185),fill=(177,137,76),width=20)
        d.arc((x-80,y-250,x+80,y-150),180,360,fill=(177,137,76),width=19)
    else:  # explorer
        d.rectangle((x-78,y+100,x+78,y+145),outline=gold,width=8)
        d.ellipse((x-22,y+106,x+22,y+150),outline=gold,width=6)
    return species,role,style

def draw_prop(image,index,t,x=540,y=900):
    kind,material,motion=prop(index)
    d=ImageDraw.Draw(image)
    if motion=="bob": y+=int(22*math.sin(t*2))
    elif motion=="sway": x+=int(32*math.sin(t*1.5))
    elif motion=="slide": x+=int(45*math.sin(t*.9))
    elif motion=="pulse": y+=int(12*math.sin(t*3))
    else: x+=int(15*math.sin(t*3))
    palette=((158,116,75),(145,158,177),(140,215,225),(135,135,141),
             (234,217,178),(187,134,162),(213,199,174),(116,168,192),
             (233,192,91),(154,231,184))
    color=palette[MATERIALS.index(material)]
    if kind in ("car","train","airplane","boat","rocket","bicycle"):
        ink=(38,47,62)
        if kind=="car":
            d.rounded_rectangle((x-145,y-30,x+145,y+65),radius=25,fill=color)
            d.polygon(((x-90,y-30),(x-50,y-95),(x+55,y-95),(x+100,y-30)),fill=color)
            d.polygon(((x-43,y-85),(x+48,y-85),(x+75,y-35),(x-70,y-35)),fill=(195,226,238))
            for dx in (-100,100): d.ellipse((x+dx-32,y+43,x+dx+32,y+107),fill=ink)
        elif kind=="train":
            d.rounded_rectangle((x-150,y-110,x+150,y+70),radius=25,fill=color)
            for dx in (-100,-25,50): d.rectangle((x+dx,y-85,x+dx+53,y-28),fill=(198,228,240))
            d.rectangle((x-125,y+50,x+125,y+85),fill=ink)
            for dx in (-95,95): d.ellipse((x+dx-27,y+66,x+dx+27,y+120),fill=ink)
        elif kind=="airplane":
            d.polygon(((x-165,y-10),(x+160,y-25),(x+195,y),(x+160,y+25),(x-165,y+10)),fill=color)
            d.polygon(((x-30,y),(x+15,y-125),(x+80,y-125),(x+50,y),(x+65,y+110),(x+15,y+110)),fill=color)
        elif kind=="boat":
            d.polygon(((x-145,y+25),(x+145,y+25),(x+100,y+105),(x-100,y+105)),fill=color)
            d.polygon(((x-10,y+15),(x-10,y-150),(x+115,y+15)),fill=(244,235,207))
            d.line((x-10,y-150,x-10,y+25),fill=ink,width=9)
        elif kind=="rocket":
            d.ellipse((x-45,y-155,x+45,y+90),fill=color)
            d.polygon(((x-45,y+40),(x-90,y+115),(x+90,y+115),(x+45,y+40)),fill=color)
            d.ellipse((x-23,y-55,x+23,y-9),fill=(198,230,242))
            flame=int(20*math.sin(t*8))
            d.polygon(((x-20,y+90),(x,y+165+flame),(x+20,y+90)),fill=(255,177,73))
        else:
            for dx in (-95,95): d.ellipse((x+dx-45,y+5,x+dx+45,y+95),outline=ink,width=12)
            d.line(((x-95,y+50),(x,y-35),(x+95,y+50),(x-95,y+50),(x+5,y+50)),fill=color,width=12)
            d.line((x,y-35,x+30,y-70),fill=color,width=9)
    elif kind in ("tree","flower","mushroom"):
        if kind=="tree":
            d.rectangle((x-19,y-10,x+19,y+140),fill=(121,88,61))
            for dx,dy in ((-60,-40),(60,-40),(0,-110)):
                d.ellipse((x+dx-75,y+dy-70,x+dx+75,y+dy+70),fill=color)
        elif kind=="flower":
            d.line((x,y+140,x,y-35),fill=(83,154,93),width=12)
            for k in range(7):
                angle=k*math.tau/7+t*.12
                px=x+58*math.cos(angle);py=y-55+58*math.sin(angle)
                d.ellipse((px-35,py-35,px+35,py+35),fill=color)
            d.ellipse((x-30,y-85,x+30,y-25),fill=(251,210,97))
        else:
            d.rounded_rectangle((x-28,y-10,x+28,y+130),radius=15,fill=(233,221,201))
            d.pieslice((x-125,y-160,x+125,y+70),180,360,fill=color)
            for dx in (-55,0,55):
                d.ellipse((x+dx-13,y-85,x+dx+13,y-59),fill=(248,241,218))
    elif kind in ("star","planet","cloud","mountain"):
        if kind=="star":
            points=[]
            for i in range(10):
                angle=-math.pi/2+i*math.pi/5
                rad=120 if i%2==0 else 50
                points.append((x+rad*math.cos(angle),y+rad*math.sin(angle)))
            d.polygon(points,fill=color)
        elif kind=="planet":
            d.ellipse((x-100,y-100,x+100,y+100),fill=color)
            d.arc((x-155,y-65,x+155,y+65),0,359,fill=(243,221,163),width=16)
        elif kind=="cloud":
            for dx,dy,rad in ((-75,15,65),(-15,-40,85),(75,0,70)):
                d.ellipse((x+dx-rad,y+dy-rad,x+dx+rad,y+dy+rad),fill=color)
            d.rectangle((x-110,y+10,x+120,y+65),fill=color)
        else:
            d.polygon(((x-155,y+125),(x,y-145),(x+155,y+125)),fill=color)
            d.polygon(((x-45,y-65),(x,y-145),(x+45,y-65),(x,y-80)),fill=(235,239,239))
    elif kind in ("clock","ball","apple","pizza","cake"):
        if kind=="clock":
            d.ellipse((x-110,y-110,x+110,y+110),fill=color)
            d.ellipse((x-95,y-95,x+95,y+95),outline=(39,47,58),width=8)
            d.line((x,y,x+int(62*math.sin(t)),y-int(62*math.cos(t))),fill=(39,47,58),width=9)
            d.line((x,y,x+43,y+30),fill=(39,47,58),width=6)
        elif kind=="ball":
            d.ellipse((x-100,y-100,x+100,y+100),fill=color)
            d.arc((x-95,y-95,x+95,y+95),-50,130,fill=(39,47,58),width=7)
        elif kind=="apple":
            d.ellipse((x-92,y-75,x+92,y+108),fill=color)
            d.line((x,y-75,x+15,y-125),fill=(98,73,48),width=10)
            d.ellipse((x+8,y-130,x+70,y-95),fill=(85,154,88))
        elif kind=="pizza":
            d.polygon(((x-130,y-95),(x+130,y-95),(x,y+140)),fill=color)
            d.line((x-130,y-95,x+130,y-95),fill=(174,120,71),width=24)
            for dx,dy in ((-45,-45),(40,-45),(0,30)):
                d.ellipse((x+dx-17,y+dy-17,x+dx+17,y+dy+17),fill=(186,73,65))
        else:
            d.rectangle((x-105,y-25,x+105,y+115),fill=color)
            d.ellipse((x-105,y-45,x+105,y-5),fill=(245,222,210))
            for dx in (-55,0,55):
                d.line((x+dx,y-45,x+dx,y-115),fill=(247,235,193),width=9)
                d.ellipse((x+dx-8,y-135,x+dx+8,y-112),fill=(252,172,75))
    elif kind in ("book","door","phone","computer","camera","gift"):
        if kind=="book":
            d.polygon(((x-105,y-115),(x,y-90),(x,y+130),(x-105,y+105)),fill=color)
            d.polygon(((x,y-90),(x+105,y-115),(x+105,y+105),(x,y+130)),fill=tuple(min(255,v+35) for v in color))
            d.line((x,y-90,x,y+130),fill=(42,48,58),width=6)
        elif kind=="door":
            d.rounded_rectangle((x-85,y-145,x+85,y+145),radius=8,fill=color,outline=(44,50,62),width=9)
            d.ellipse((x+42,y-5,x+58,y+11),fill=(242,215,135))
        elif kind=="phone":
            d.rounded_rectangle((x-70,y-145,x+70,y+145),radius=18,fill=(37,43,55),outline=color,width=12)
            d.rectangle((x-52,y-112,x+52,y+95),fill=(125,192,216))
            d.ellipse((x-9,y+111,x+9,y+129),fill=(219,224,225))
        elif kind=="computer":
            d.rounded_rectangle((x-135,y-110,x+135,y+85),radius=12,fill=(39,47,59),outline=color,width=13)
            d.rectangle((x-112,y-90,x+112,y+62),fill=(123,193,215))
            d.line((x,y+85,x,y+133),fill=color,width=19)
            d.line((x-70,y+137,x+70,y+137),fill=color,width=14)
        elif kind=="camera":
            d.rounded_rectangle((x-130,y-65,x+130,y+90),radius=20,fill=color)
            d.rectangle((x-85,y-100,x-5,y-60),fill=color)
            d.ellipse((x-65,y-60,x+65,y+70),fill=(42,50,65))
            d.ellipse((x-42,y-37,x+42,y+47),fill=(143,207,225))
        else:
            d.rectangle((x-105,y-75,x+105,y+115),fill=color)
            d.line((x,y-75,x,y+115),fill=(245,227,189),width=17)
            d.line((x-105,y+10,x+105,y+10),fill=(245,227,189),width=17)
            d.arc((x-60,y-130,x+60,y-50),0,180,fill=(245,227,189),width=12)
    elif kind in ("cup","bottle","umbrella","lamp","key","hat"):
        if kind=="cup":
            d.polygon(((x-90,y-65),(x+65,y-65),(x+45,y+115),(x-65,y+115)),fill=color)
            d.arc((x+25,y-50,x+135,y+80),-90,90,fill=color,width=17)
        elif kind=="bottle":
            d.rounded_rectangle((x-62,y-55,x+62,y+130),radius=19,fill=color)
            d.rectangle((x-25,y-125,x+25,y-55),fill=color)
            d.rectangle((x-32,y-135,x+32,y-115),fill=(43,52,65))
        elif kind=="umbrella":
            d.pieslice((x-135,y-160,x+135,y+105),180,360,fill=color)
            d.line((x,y-30,x,y+140),fill=(49,53,65),width=10)
            d.arc((x-2,y+100,x+65,y+165),0,180,fill=(49,53,65),width=10)
        elif kind=="lamp":
            d.polygon(((x-90,y-110),(x+90,y-110),(x+125,y+15),(x-125,y+15)),fill=color)
            d.line((x,y+15,x,y+145),fill=(48,53,62),width=13)
            d.line((x-75,y+145,x+75,y+145),fill=(48,53,62),width=15)
        elif kind=="key":
            d.ellipse((x-115,y-110,x-15,y-10),outline=color,width=22)
            d.line((x-12,y-10,x+120,y+120),fill=color,width=22)
            d.line((x+75,y+80,x+110,y+40),fill=color,width=17)
        else:
            d.ellipse((x-85,y-115,x+85,y+20),fill=color)
            d.rectangle((x-135,y-10,x+135,y+15),fill=color)
    elif kind in ("chair","table","chest","guitar","house","castle","bridge","shoe","backpack","telescope"):
        ink=(42,49,60)
        if kind=="chair":
            d.rounded_rectangle((x-85,y-140,x+85,y+35),radius=12,fill=color)
            d.rectangle((x-105,y+25,x+105,y+58),fill=color)
            for dx in (-75,75): d.line((x+dx,y+58,x+dx,y+155),fill=ink,width=17)
        elif kind=="table":
            d.rounded_rectangle((x-145,y-20,x+145,y+28),radius=9,fill=color)
            for dx in (-105,105): d.line((x+dx,y+25,x+dx,y+155),fill=ink,width=20)
        elif kind=="chest":
            d.rounded_rectangle((x-125,y-75,x+125,y+125),radius=15,fill=color,outline=ink,width=9)
            d.arc((x-125,y-145,x+125,y-10),180,360,fill=color,width=26)
            d.rectangle((x-16,y+0,x+16,y+55),fill=(244,211,113))
            d.line((x-125,y+20,x+125,y+20),fill=ink,width=8)
        elif kind=="guitar":
            d.ellipse((x-100,y-20,x+75,y+165),fill=color,outline=ink,width=6)
            d.ellipse((x-75,y-105,x+55,y+30),fill=color)
            d.line((x-8,y-60,x+65,y-205),fill=(125,84,58),width=29)
            for dx in (-8,0,8): d.line((x+dx,y+130,x+dx+69,y-194),fill=(234,223,195),width=2)
        elif kind=="house":
            d.rectangle((x-105,y-40,x+105,y+130),fill=color)
            d.polygon(((x-145,y-40),(x,y-165),(x+145,y-40)),fill=(157,89,83))
            d.rectangle((x-26,y+38,x+30,y+130),fill=ink)
            for dx in (-70,70): d.rectangle((x+dx-17,y-5,x+dx+17,y+32),fill=(190,225,239))
        elif kind=="castle":
            d.rectangle((x-105,y-45,x+105,y+145),fill=color)
            for dx in (-105,105):
                d.rectangle((x+dx-35,y-125,x+dx+35,y+145),fill=color)
                for off in (-27,13): d.rectangle((x+dx+off,y-148,x+dx+off+15,y-115),fill=color)
            d.arc((x-35,y+48,x+35,y+148),180,360,fill=ink,width=17)
        elif kind=="bridge":
            d.line((x-150,y+30,x+150,y+30),fill=color,width=24)
            for dx in (-110,110): d.line((x+dx,y-90,x+dx,y+145),fill=ink,width=17)
            d.arc((x-105,y-65,x+105,y+105),0,180,fill=color,width=14)
        elif kind=="shoe":
            d.polygon(((x-125,y-35),(x-20,y-35),(x+35,y+55),(x+130,y+70),(x+145,y+120),(x-135,y+120)),fill=color)
            d.line((x-135,y+115,x+145,y+115),fill=ink,width=15)
            for dy in (20,42,64): d.line((x-30,y+dy,x+27,y+dy),fill=(233,225,208),width=6)
        elif kind=="backpack":
            d.rounded_rectangle((x-100,y-100,x+100,y+135),radius=36,fill=color,outline=ink,width=7)
            d.arc((x-45,y-160,x+45,y-70),180,360,fill=ink,width=12)
            d.rounded_rectangle((x-70,y+35,x+70,y+110),radius=12,outline=ink,width=8)
            for dx in (-105,105): d.line((x+dx,y-55,x+dx,y+105),fill=ink,width=12)
        else:  # telescope
            d.polygon(((x-135,y-85),(x+90,y-135),(x+120,y-55),(x-100,y+5)),fill=color)
            d.line((x,y-15,x,y+150),fill=ink,width=13)
            d.line((x,y+30,x-95,y+145),fill=ink,width=12)
            d.line((x,y+30,x+95,y+145),fill=ink,width=12)
    else:
        d.rounded_rectangle((x-100,y-120,x+100,y+120),radius=22,fill=color)
        d.rectangle((x-60,y-55,x+60,y+55),outline=(39,47,58),width=6)
    return kind,material,motion


# Second-pass art direction: styles affect visible anatomy, facial expression,
# and markings instead of relying only on the catalog index or base palette.
_base_draw_character = draw_character
_base_draw_prop = draw_prop

def draw_character(image, index, t, x=540, y=900):
    species, role, style = _base_draw_character(image, index, t, x, y)
    d = ImageDraw.Draw(image)
    bob = int(14 * math.sin(t * 2.2))
    cy = y + bob
    ink = (32, 43, 58)
    light = (246, 238, 220)
    # Blinking and shifting pupils create expressions that animate in time.
    blink = math.sin(t * 3.3 + index * 0.13) > 0.965
    glance = int(7 * math.sin(t * 1.7 + index * 0.07))
    for side in (-1, 1):
        ex = x + side * 42
        ey = cy - 56
        if blink:
            d.arc((ex-19, ey-4, ex+19, ey+9), 0, 180, fill=ink, width=5)
        else:
            d.ellipse((ex-19, ey-22, ex+19, ey+22), fill=light)
            d.ellipse((ex-7+glance, ey-8, ex+7+glance, ey+9), fill=ink)
            d.ellipse((ex-4+glance, ey-7, ex+1+glance, ey-2), fill=(255,255,255))
    smile = int(6 * math.sin(t * 2 + index))
    d.arc((x-29, cy-9+smile, x+29, cy+38+smile), 8, 170, fill=ink, width=5)
    if style == "striped":
        for k in range(4):
            yy = cy - 139 + k * 30
            d.arc((x-79, yy, x+79, yy+25), 15, 165, fill=(242,213,149), width=8)
    elif style == "spotted":
        for dx, dy, rad in ((-75,-120,12),(72,-114,17),(-69,9,15),(65,27,11)):
            d.ellipse((x+dx-rad,cy+dy-rad,x+dx+rad,cy+dy+rad),fill=(235,202,135))
    elif style == "angular":
        d.polygon(((x-88,cy-130),(x-43,cy-179),(x,cy-137),(x+46,cy-180),(x+88,cy-130)),outline=ink)
    elif style == "soft":
        for dx in (-67,67):
            d.ellipse((x+dx-19,cy+2,x+dx+19,cy+30),fill=(242,157,155))
    elif style == "bright":
        d.arc((x-107,cy-185,x+107,cy+70),190,325,fill=(255,239,115),width=12)
    elif style == "dark":
        d.arc((x-110,cy-182,x+110,cy+74),25,160,fill=(35,42,62),width=15)
    elif style == "tall":
        d.line((x-65,cy+89,x-75,cy+156),fill=ink,width=14)
        d.line((x+65,cy+89,x+75,cy+156),fill=ink,width=14)
    elif style == "tiny":
        d.ellipse((x-34,cy+84,x-10,cy+107),fill=ink)
        d.ellipse((x+10,cy+84,x+34,cy+107),fill=ink)
    elif style == "round":
        d.arc((x-130,cy-170,x+130,cy+106),30,145,fill=light,width=9)
    return species, role, style

def draw_prop(image, index, t, x=540, y=900):
    kind, material, motion = _base_draw_prop(image, index, t, x, y)
    d = ImageDraw.Draw(image)
    # The underlying renderer shifts most props in time. Texture follows
    # that motion to keep it attached to the prop rather than the backdrop.
    px = x
    py = y
    accent = (244, 237, 215)
    if material == "wood":
        for dy in (-25,5,35):
            d.arc((px-70,py+dy-16,px+70,py+dy+16),5,170,fill=(117,75,48),width=3)
    elif material == "metal":
        for k in range(3):
            d.line((px-70+k*24,py-48,px-30+k*24,py+48),fill=(214,228,237),width=4)
    elif material == "glass":
        d.line((px-48,py-60,px-22,py+28),fill=(224,250,252),width=9)
    elif material == "stone":
        for dx,dy in ((-40,-22),(29,15),(-14,48)):
            d.line((px+dx-13,py+dy,px+dx+7,py+dy-10,px+dx+18,py+dy+3),fill=(90,98,104),width=3)
    elif material == "fabric":
        for dx in range(-55,56,22):
            d.line((px+dx,py-35,px+dx+18,py+45),fill=(235,219,196),width=2)
    elif material == "paper":
        d.line((px-42,py-25,px+42,py-25),fill=(180,174,156),width=3)
        d.line((px-42,py-6,px+26,py-6),fill=(180,174,156),width=3)
    elif material == "ceramic":
        d.arc((px-63,py-60,px+63,py+64),195,300,fill=accent,width=7)
    elif material == "plastic":
        d.ellipse((px-47,py-44,px-25,py-22),fill=(255,255,255))
    elif material == "gold":
        d.arc((px-75,py-75,px+75,py+75),205,320,fill=(255,242,160),width=9)
    elif material == "neon":
        d.arc((px-87,py-88,px+87,py+88),185,350,fill=(165,250,255),width=6)
    return kind, material, motion


# Third-pass silhouette design. A separate rig is drawn for every species;
# these designs are intentionally independent of the original shared oval.
def draw_character_silhouette(image, index, t, x=540, y=900,
                              expression="neutral", gesture="idle"):
    if expression not in ("neutral", "surprised", "happy", "focused"):
        raise ValueError(f"unsupported facial expression: {expression}")
    if gesture not in ("idle", "point", "celebrate", "carry", "carry_rig"):
        raise ValueError(f"unsupported gesture: {gesture}")
    species, role, style = character(index)
    d = ImageDraw.Draw(image)
    phase = math.sin(t * 2.5 + index * .031)
    y += int(12 * phase)
    palettes = {
        "human":(227,172,125),"robot":(126,175,203),"cat":(218,154,97),
        "dog":(179,132,89),"fox":(239,129,68),"rabbit":(226,212,201),
        "bear":(141,101,79),"owl":(151,113,88),"bird":(88,173,203),
        "frog":(99,192,104),"turtle":(87,156,108),"fish":(93,184,213),
        "mouse":(169,160,170),"monkey":(174,121,81),"lion":(220,166,76),
        "penguin":(64,77,91),"deer":(174,124,84),"dragon":(101,165,135),
        "alien":(132,202,158),"ghost":(226,231,240)
    }
    color = palettes[species]
    dark = (42,49,61)
    w = 66 if style == "tiny" else 116 if style == "round" else 82
    if species == "fish":
        d.ellipse((x-125,y-88,x+110,y+65),fill=color)
        d.polygon(((x-105,y-7),(x-206,y-95),(x-206,y+83)),fill=color)
        d.polygon(((x-10,y-78),(x+25,y-147),(x+64,y-73)),fill=color)
    elif species == "ghost":
        d.pieslice((x-104,y-190,x+104,y+25),180,360,fill=color)
        d.rectangle((x-104,y-85,x+104,y+97),fill=color)
        for dx in (-69,0,69):
            d.ellipse((x+dx-37,y+55,x+dx+37,y+122),fill=color)
    elif species == "robot":
        d.rounded_rectangle((x-94,y-154,x+94,y+37),radius=17,fill=color,outline=dark,width=8)
        d.rectangle((x-55,y+36,x+55,y+129),fill=(90,128,155))
        d.line((x,y-154,x,y-206),fill=dark,width=9)
        d.ellipse((x-15,y-226,x+15,y-196),fill=(246,188,89))
    elif species in ("bird","owl","penguin"):
        d.ellipse((x-105,y-158,x+105,y+131),fill=color)
        for side in (-1,1):
            d.ellipse((x+side*85-45,y-28,x+side*85+45,y+86),fill=(color[0]//2,color[1]//2,color[2]//2))
        d.polygon(((x-24,y-25),(x+24,y-25),(x,y+13)),fill=(240,177,79))
        if species=="penguin":
            d.ellipse((x-67,y-76,x+67,y+117),fill=(239,235,223))
        if species=="owl":
            for dx in (-43,43):
                d.ellipse((x+dx-45,y-113,x+dx+45,y-33),fill=(239,219,180))
    elif species=="turtle":
        d.ellipse((x-142,y-74,x+142,y+155),fill=(67,113,78),outline=dark,width=7)
        d.ellipse((x-99,y-44,x+99,y+126),fill=color)
        d.ellipse((x-62,y-181,x+62,y-54),fill=(112,186,115))
        for dx in (-105,105):
            d.ellipse((x+dx-37,y+104,x+dx+37,y+163),fill=color)
    elif species=="dragon":
        d.ellipse((x-w,y-147,x+w,y+96),fill=color)
        for side in (-1,1):
            d.polygon(((x+side*65,y-33),(x+side*182,y-148),(x+side*136,y+83)),fill=(77,129,115))
        for dx in (-53,0,53):
            d.polygon(((x+dx-22,y-142),(x+dx,y-222),(x+dx+22,y-142)),fill=(228,188,105))
    elif species=="alien":
        d.ellipse((x-126,y-176,x+126,y+43),fill=color)
        d.rounded_rectangle((x-56,y+29,x+56,y+145),radius=28,fill=color)
    else:
        d.ellipse((x-w,y-146,x+w,y+56),fill=color)
        d.rounded_rectangle((x-60,y+30,x+60,y+158),radius=25,fill=color)
        if species in ("cat","fox","rabbit","mouse","bear","lion","deer"):
            height=135 if species=="rabbit" else 75
            for side in (-1,1):
                d.polygon(((x+side*48,y-113),(x+side*80,y-165-height),(x+side*91,y-96)),fill=color)
        if species=="dog":
            for side in (-1,1):
                d.ellipse((x+side*94-35,y-142,x+side*94+35,y+5),fill=(116,83,67))
        if species=="lion":
            d.ellipse((x-128,y-187,x+128,y+77),outline=(180,107,48),width=35)
        if species=="frog":
            for dx in (-69,69):
                d.ellipse((x+dx-39,y-184,x+dx+39,y-108),fill=color)
        if species=="deer":
            for side in (-1,1):
                d.line((x+side*48,y-145,x+side*112,y-263),fill=(117,82,60),width=11)
                d.line((x+side*88,y-217,x+side*145,y-238),fill=(117,82,60),width=8)
        if species=="monkey":
            for dx in (-91,91):
                d.ellipse((x+dx-35,y-80,x+dx+35,y+11),fill=(221,177,139))
    # Articulated extremities are species-aware and driven by time, not index alone.
    gait = math.sin(t * 5.0 + index * .09)
    swing = int(36 * gait)
    if species in ("human","robot","cat","dog","fox","rabbit","bear","frog",
                   "mouse","monkey","lion","deer","alien"):
        for side in (-1,1):
            shoulder=(x+side*58,y+55)
            elbow=(x+side*(105+swing//3),y+93+side*swing)
            hand=(x+side*(122+swing//2),y+138+side*swing)
            if gesture != "carry_rig":
                d.line((shoulder,elbow,hand),fill=dark,width=15,joint="curve")
                d.ellipse((hand[0]-13,hand[1]-13,hand[0]+13,hand[1]+13),fill=color)
            hip=(x+side*32,y+147)
            knee=(x+side*(40+swing//2),y+197)
            foot=(x+side*(43+swing),y+247-abs(swing)//3)
            d.line((hip,knee,foot),fill=dark,width=17,joint="curve")
            d.ellipse((foot[0]-21,foot[1]-10,foot[0]+21,foot[1]+11),fill=color)
    elif species in ("bird","owl","penguin","dragon"):
        flap = int(42 * math.sin(t*6.0+index*.07))
        for side in (-1,1):
            d.polygon(((x+side*65,y-20),
                       (x+side*160,y-75-flap),
                       (x+side*116,y+77-flap//2)),fill=color,outline=dark)
    elif species=="fish":
        tail=int(32*math.sin(t*7+index*.03))
        d.polygon(((x-106,y-9),(x-203,y-92+tail),(x-203,y+79+tail)),fill=color,outline=dark)
    elif species=="turtle":
        for side in (-1,1):
            reach=int(18*math.sin(t*3.0+side*1.5))
            d.ellipse((x+side*133-32,y+23+reach,x+side*133+32,y+87+reach),fill=color,outline=dark,width=4)
    elif species=="ghost":
        for side in (-1,1):
            reach=int(25*math.sin(t*2.4+side))
            d.ellipse((x+side*105-24,y-9+reach,x+side*105+24,y+43+reach),fill=color)
    # Facial reactions belong to the production silhouette renderer.
    blink = expression == "neutral" and math.sin(t*3.3+index*.13)>.965
    eye_y = y-69 if species not in ("turtle","fish") else y-91
    for dx in (-38,38):
        if expression == "happy":
            d.arc((x+dx-17,eye_y-12,x+dx+17,eye_y+13),180,360,fill=dark,width=6)
        elif expression == "surprised":
            d.ellipse((x+dx-18,eye_y-20,x+dx+18,eye_y+20),fill=(245,243,229))
            d.ellipse((x+dx-9,eye_y-10,x+dx+9,eye_y+11),fill=dark)
        elif blink:
            d.line((x+dx-14,eye_y,x+dx+14,eye_y),fill=dark,width=5)
        else:
            d.ellipse((x+dx-14,eye_y-16,x+dx+14,eye_y+16),fill=(245,243,229))
            shift=int(5*math.sin(t*1.6+index*.07))
            d.ellipse((x+dx-6+shift,eye_y-6,x+dx+6+shift,eye_y+8),fill=dark)
            if expression == "focused":
                d.line((x+dx-19,eye_y-24,x+dx+18,eye_y-18),fill=dark,width=6)
    if expression == "surprised":
        d.ellipse((x-13,y-35,x+13,y-3),fill=dark)
    elif expression == "focused":
        d.line((x-21,y-17,x+21,y-17),fill=dark,width=5)
    elif species not in ("bird","owl","penguin"):
        d.arc((x-23,y-44,x+23,y+4),8,170,fill=dark,width=5)
    # Overlay gestures for all species: paws/arms, wings, fins and ghostly
    # appendages must each respond to the same authored story action.
    if gesture != "idle":
        for side in (-1,1):
            if gesture == "celebrate":
                hand=(x+side*135,y-145-int(12*math.sin(t*5+side)))
            elif gesture == "point" and side == 1:
                hand=(x+215,y+15)
            elif gesture == "carry":
                hand=(x+side*78,y+145)
            else:
                continue
            d.line(((x+side*58,y+55),hand),fill=dark,width=19)
            d.ellipse((hand[0]-13,hand[1]-13,hand[0]+13,hand[1]+13),fill=color)
    return species,role,style

# Use the new silhouette rig for character production, retaining the catalog
# and opt-in renderer contract.
draw_character = draw_character_silhouette
