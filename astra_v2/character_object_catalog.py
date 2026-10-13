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

def draw_character(image,index,t,x=540,y=900):
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
    for dx in (-48,48):
        if abs(math.sin(t*1.5))>.99:
            d.line((x+dx-14,y-45,x+dx+14,y-45),fill=(24,29,38),width=6)
        else:
            d.ellipse((x+dx-13,y-60,x+dx+13,y-32),fill=(24,29,38))
    d.arc((x-32,y-20,x+32,y+28),0,180,fill=(35,37,43),width=5)
    d.ellipse((x-95,y+55,x+95,y+270),fill=base)
    step=int(30*math.sin(t*4))
    for side in (-1,1):
        d.line((x+side*52,y+235,x+side*52+side*step,y+325),fill=base,width=27)
        d.line((x+side*85,y+90,x+side*145,y+125+side*step),fill=base,width=19)
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
        d.rounded_rectangle((x-140,y-45,x+140,y+70),radius=25,fill=color)
        for dx in (-90,90): d.ellipse((x+dx-30,y+50,x+dx+30,y+110),fill=(40,48,58))
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
        d.ellipse((x-115,y-115,x+115,y+115),fill=color)
    elif kind in ("clock","ball","apple","pizza","cake"):
        d.ellipse((x-95,y-95,x+95,y+95),fill=color)
        d.ellipse((x-15,y-15,x+15,y+15),fill=(40,48,58))
    else:
        d.rounded_rectangle((x-100,y-120,x+100,y+120),radius=22,fill=color)
        d.rectangle((x-60,y-55,x+60,y+55),outline=(39,47,58),width=6)
    return kind,material,motion
