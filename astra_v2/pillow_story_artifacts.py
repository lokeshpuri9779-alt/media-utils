"""Dedicated story-object illustrations for ASTRA's deterministic Pillow renderer.

These are semantic prop drawings, not randomized motif substitutions. Damage
marks are object-attached and contract smoothly during an authored repair.
"""
from __future__ import annotations
import math

INK=(39,47,61)
GOLD=(224,177,91)
PAPER=(246,231,194)

def draw_story_prop(d,name,x,y,t=0,*,action="idle",condition=None,repair_transition=False):
    x,y=int(x),int(y)
    if name=="key":
        d.ellipse((x-92,y-55,x+10,y+47),fill=GOLD,outline=INK,width=8)
        d.ellipse((x-63,y-27,x-19,y+17),fill=(78,91,103),outline=INK,width=5)
        d.line((x-5,y+25,x+112,y+142),fill=GOLD,width=24)
        d.line((x+65,y+105,x+105,y+65),fill=GOLD,width=18)
        d.line((x+91,y+132,x+130,y+93),fill=GOLD,width=18)
    elif name=="bell":
        d.arc((x-49,y-104,x+49,y-24),180,360,fill=INK,width=9)
        d.pieslice((x-90,y-66,x+90,y+111),180,360,fill=(226,183,105),outline=INK,width=8)
        d.rectangle((x-88,y+18,x+88,y+76),fill=(226,183,105),outline=INK,width=7)
        d.ellipse((x-28,y+72,x+28,y+119),fill=(179,124,73),outline=INK,width=6)
        d.line((x-105,y+30,x-127,y+5),fill=GOLD,width=6)
        d.line((x+105,y+30,x+127,y+5),fill=GOLD,width=6)
    elif name=="compass":
        d.ellipse((x-112,y-112,x+112,y+112),fill=(190,151,91),outline=INK,width=10)
        d.ellipse((x-91,y-91,x+91,y+91),fill=PAPER,outline=INK,width=5)
        d.polygon(((x,y-77),(x+24,y),(x,y+77),(x-24,y)),fill=(184,73,70),outline=INK)
        d.polygon(((x,y-77),(x-24,y),(x,y+77),(x+24,y)),fill=(83,124,156),outline=INK)
        for a in range(4):
            q=a*math.pi/2
            d.ellipse((x+int(73*math.cos(q))-6,y+int(73*math.sin(q))-6,x+int(73*math.cos(q))+6,y+int(73*math.sin(q))+6),fill=INK)
    elif name=="shield":
        d.polygon(((x-100,y-105),(x+100,y-105),(x+88,y+35),(x,y+132),(x-88,y+35)),fill=(104,143,173),outline=INK)
        d.line((x,y-84,x,y+95),fill=(229,207,151),width=12)
        d.line((x-70,y-5,x+70,y-5),fill=(229,207,151),width=12)
        d.polygon(((x,y-55),(x+18,y-8),(x,y+40),(x-18,y-8)),fill=(233,190,101))
    elif name=="rocket":
        d.polygon(((x,y-145),(x+64,y-50),(x+55,y+77),(x-55,y+77),(x-64,y-50)),fill=(190,199,204),outline=INK)
        d.ellipse((x-26,y-54,x+26,y-2),fill=(103,173,191),outline=INK,width=6)
        d.polygon(((x-55,y+25),(x-116,y+94),(x-47,y+75)),fill=(188,83,78),outline=INK)
        d.polygon(((x+55,y+25),(x+116,y+94),(x+47,y+75)),fill=(188,83,78),outline=INK)
        flame= int(12*math.sin(float(t)*7))
        d.polygon(((x-31,y+75),(x,y+157+flame),(x+31,y+75)),fill=(240,139,72))
        d.polygon(((x-14,y+82),(x,y+125+flame),(x+14,y+82)),fill=(255,218,125))
    elif name=="heart":
        d.ellipse((x-96,y-91,x+8,y+25),fill=(205,91,99),outline=INK,width=7)
        d.ellipse((x-8,y-91,x+96,y+25),fill=(205,91,99),outline=INK,width=7)
        d.polygon(((x-94,y-25),(x+94,y-25),(x,y+128)),fill=(205,91,99),outline=INK)
        d.arc((x-62,y-65,x+3,y+26),190,285,fill=(248,185,178),width=7)
    elif name=="wrench":
        d.line((x-65,y+95,x+70,y-48),fill=(164,178,190),width=39)
        d.arc((x-112,y-132,x+38,y+22),205,330,fill=(164,178,190),width=31)
        d.line((x+43,y-79,x+104,y-141),fill=(164,178,190),width=32)
        d.ellipse((x-83,y+76,x-47,y+112),fill=(84,98,112))
    elif name=="clock":
        d.ellipse((x-112,y-112,x+112,y+112),fill=(184,133,83),outline=INK,width=9)
        d.ellipse((x-91,y-91,x+91,y+91),fill=(249,235,199),outline=INK,width=6)
        for a in range(12):
            q=a*math.pi/6
            px=x+int(72*math.sin(q)); py=y-int(72*math.cos(q))
            d.ellipse((px-5,py-5,px+5,py+5),fill=INK)
        d.line((x,y,x,y-58),fill=INK,width=9)
        d.line((x,y,x+48,y+22),fill=INK,width=8)
        d.ellipse((x-9,y-9,x+9,y+9),fill=GOLD,outline=INK,width=3)
    if condition=="damaged":
        # Distinct visible crack/impact mark across the actual illustrated prop.
        d.line((x-48,y-34,x-12,y-5,x-29,y+26,x+8,y+55),fill=(69,49,52),width=8,joint="curve")
        d.line((x-12,y-5,x+23,y-23),fill=(69,49,52),width=6)
        if name in ("clock","compass"):
            d.ellipse((x+35,y-5,x+55,y+15),fill=(54,48,54))
    elif condition=="repaired" and repair_transition:
        progress=max(0.0,min(1.0,(float(t)-.2)/1.15))
        d.line((x-48,y-34,x-12,y-5,x-29,y+26,x+8,y+55),fill=(69,49,52),width=max(1,round(8*(1-progress))))
    elif condition=="repaired":
        d.ellipse((x+72,y-112,x+112,y-72),fill=(255,225,139),outline=INK,width=3)
    return True
