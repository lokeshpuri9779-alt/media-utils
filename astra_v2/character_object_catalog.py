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
    # Role identity is represented by an animated badge; distinct roles still
    # require bespoke costume designs before commercial-quality approval.
    d.ellipse((x-24,y+120,x+24,y+168),outline=(248,217,136),width=7)
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
        d.rectangle((x-17,y-10,x+17,y+140),fill=(121,88,61))
        d.ellipse((x-110,y-150,x+110,y+35),fill=color)
    elif kind in ("star","planet","cloud","mountain"):
        d.ellipse((x-115,y-115,x+115,y+115),fill=color)
    elif kind in ("clock","ball","apple","pizza","cake"):
        d.ellipse((x-95,y-95,x+95,y+95),fill=color)
        d.ellipse((x-15,y-15,x+15,y+15),fill=(40,48,58))
    else:
        d.rounded_rectangle((x-100,y-120,x+100,y+120),radius=22,fill=color)
        d.rectangle((x-60,y-55,x+60,y+55),outline=(39,47,58),width=6)
    return kind,material,motion
