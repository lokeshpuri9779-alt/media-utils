"""Articulated animal prototypes and visibly distinct object states.

Uses deterministic procedural 2D geometry; not biological animation or physics.
"""
from __future__ import annotations
import math
from PIL import Image,ImageDraw
from experimental.item_renderer import render_item

ANIMALS=("dog","cat","rabbit","bird","fish")
STATES=("intact","damaged","repaired","open","closed")

def animal_frame(species: str, t: float, size: int=192) -> Image.Image:
    if species not in ANIMALS: raise ValueError("unsupported species")
    if size<32: raise ValueError("invalid size")
    im=Image.new("RGBA",(size,size),(0,0,0,0))
    d=ImageDraw.Draw(im)
    s=size/192
    def ell(box,color):
        d.ellipse(tuple(round(v*s) for v in box),fill=color)
    def line(points,color,width):
        d.line([(round(x*s),round(y*s)) for x,y in points],fill=color,width=max(1,round(width*s)))
    fur={"dog":(188,128,81),"cat":(136,144,165),"rabbit":(231,222,215),
         "bird":(100,164,210),"fish":(96,179,186)}[species]
    phase=math.sin(t*9)
    if species=="fish":
        ell((49,72,145,131),fur)
        d.polygon([(round(x*s),round(y*s)) for x,y in ((49,99),(19,67+phase*9),(19,133+phase*9))],fill=fur)
        ell((118,91,124,97),(31,37,44))
        line([(77,82),(94,66),(104,84)],(65,132,146),6)
    elif species=="bird":
        ell((56,81,141,137),fur)
        ell((113,59,153,98),fur)
        d.polygon([(round(x*s),round(y*s)) for x,y in ((149,77),(171,86),(149,95))],fill=(234,171,69))
        ell((135,72,141,78),(34,41,52))
        ell((67,91+phase*9,119,119+phase*9),(67,125,180))
        for x in (87,120):
            line([(x,133),(x,158)],(129,92,65),4)
    else:
        ell((43,93,139,139),fur)
        ell((114,66,163,115),fur)
        if species=="rabbit":
            ell((123,22,136,80),fur);ell((144,22,157,80),fur)
        elif species=="cat":
            d.polygon([(round(x*s),round(y*s)) for x,y in ((120,79),(121,48),(137,68))],fill=fur)
            d.polygon([(round(x*s),round(y*s)) for x,y in ((144,68),(160,48),(159,84))],fill=fur)
        else:
            ell((115,53,133,87),(138,91,65));ell((149,54,169,88),(138,91,65))
        for x,offset in ((61,1),(84,-1),(114,-1),(134,1)):
            y=132+abs(phase)*8
            line([(x,y),(x+phase*8*offset,164-abs(phase)*9)],fur,10)
        line([(45,109),(27,95+phase*12),(20,99+phase*12)],fur,9)
        ell((145,88,151,94),(30,36,44))
        ell((162,102,168,108),(45,43,47))
    return im

def item_state_frame(kind: str, category: str, state: str, size: int=192) -> Image.Image:
    if state not in STATES: raise ValueError("unsupported state")
    base=render_item(kind,category,size=size).convert("RGBA")
    d=ImageDraw.Draw(base)
    s=size/192
    if state=="damaged":
        pts=[(80,40),(103,75),(88,106),(115,140)]
        d.line([(round(x*s),round(y*s)) for x,y in pts],fill=(47,47,53,255),width=max(2,round(5*s)))
    elif state=="repaired":
        d.ellipse(tuple(round(v*s) for v in (132,12,183,63)),fill=(76,175,111,255))
        d.line([(round(x*s),round(y*s)) for x,y in ((143,37),(154,48),(173,25))],fill=(255,255,255,255),width=max(2,round(6*s)))
    elif state=="open":
        d.rectangle(tuple(round(v*s) for v in (56,72,139,88)),fill=(42,54,69,255))
    elif state=="closed":
        d.rectangle(tuple(round(v*s) for v in (56,72,139,88)),fill=(168,174,181,255))
    return base
