"""Render simple recognizable procedural world icons without external asset files.

First visual adapter for ASTRA's semantic world library. Shapes are intentionally
basic prototypes, not production character models.
"""
from __future__ import annotations
import math
from PIL import Image, ImageDraw
from experimental.world_library import make_asset

COLORS={"red":(224,87,80),"orange":(243,158,65),"yellow":(241,207,91),
"green":(88,173,116),"cyan":(86,191,204),"blue":(91,132,210),
"purple":(150,106,195),"pink":(228,133,168),"white":(229,231,224),
"black":(62,67,77),"brown":(161,111,75),"gray":(148,154,163)}

def draw_asset(category: str, seed: str, t: float=0, size: int=192) -> Image.Image:
    if size<32: raise ValueError("size must be >= 32")
    asset=make_asset(category,seed)
    image=Image.new("RGB",(size,size),(238,243,248))
    d=ImageDraw.Draw(image)
    color=COLORS[asset.color]
    s=size/192
    def ellipse(box,fill):
        d.ellipse(tuple(round(v*s) for v in box),fill=fill)
    def rect(box,fill):
        d.rectangle(tuple(round(v*s) for v in box),fill=fill)
    def line(points,fill,width=4):
        d.line([(round(x*s),round(y*s)) for x,y in points],fill=fill,width=max(1,round(width*s)))
    sway=math.sin(t*2)*6
    if category=="animals":
        # Quadruped silhouette: head, ears, four feet, face.
        ellipse((42,90,147,142),color)
        ellipse((119,65,168,112),color)
        ellipse((125,58,140,83),color)
        ellipse((150,60,163,86),color)
        for x in (58,83,113,137):
            rect((x,130,x+12,161),color)
        ellipse((149,88,155,94),(30,38,48))
        ellipse((164,100,170,106),(30,38,48))
        line([(43,106),(27,91),(20,95)],color,7)
    elif category=="flora":
        line([(96,161),(96+sway*.4,65)],(91,125,75),12)
        for x,y,r in ((70,93,24),(112,79,28),(91,52,30),(130,112,21)):
            ellipse((x-r+sway,y-r,x+r+sway,y+r),(76,161,97))
        ellipse((82+sway,68,96+sway,82),color)
    elif category=="vehicles":
        rect((32,102,162,140),color)
        d.polygon([(round(x*s),round(y*s)) for x,y in ((54,102),(75,73),(127,73),(145,102))],fill=color)
        rect((81,79,118,100),(177,222,240))
        for x in (62,136):
            ellipse((x-16,130,x+16,162),(42,51,64))
            ellipse((x-7,139,x+7,153),(190,198,204))
    elif category=="architecture":
        rect((48,76,150,165),color)
        d.polygon([(round(x*s),round(y*s)) for x,y in ((35,78),(99,31),(163,78))],fill=(109,79,80))
        rect((87,119,112,165),(103,77,63))
        for x in (61,124):
            rect((x-9,90,x+9,110),(174,215,234))
    elif category=="food":
        ellipse((38,84,154,151),color)
        ellipse((55,97,137,133),(248,221,155))
        for x,y in ((78,110),(111,116),(97,125)):
            ellipse((x-5,y-5,x+5,y+5),(200,75,69))
    elif category=="nature":
        d.polygon([(round(x*s),round(y*s)) for x,y in ((17,151),(88,45),(165,151))],fill=color)
        d.polygon([(round(x*s),round(y*s)) for x,y in ((61,86),(88,45),(114,86),(95,80),(84,90))],fill=(243,245,247))
    elif category=="fantasy":
        ellipse((44,55,151,157),color)
        for x in (77,118):
            ellipse((x-9,91,x+9,109),(255,255,255))
            ellipse((x-3,96,x+3,104),(36,42,53))
        line([(83,130),(99,137),(117,130)],(45,51,61),4)
        d.polygon([(round(x*s),round(y*s)) for x,y in ((65,64),(80,28),(93,62))],fill=color)
    elif category=="furniture":
        rect((44,105,150,125),color)
        rect((45,65,61,160),color)
        rect((134,119,148,163),color)
        rect((64,119,76,163),color)
    elif category=="tools":
        line([(65,151),(121,58)],(131,107,78),15)
        rect((93,45,149,72),color)
    else: # products
        rect((62,39,133,157),color)
        rect((70,49,125,139),(214,226,235))
        ellipse((93,145,103,155),(240,243,245))
    return image

def contact_sheet(seed: str="demo", size: int=192) -> Image.Image:
    from experimental.world_library import TAXONOMY
    categories=tuple(TAXONOMY)
    sheet=Image.new("RGB",(size*5,size*2),(255,255,255))
    for i,category in enumerate(categories):
        tile=draw_asset(category,seed+category,size=size)
        sheet.paste(tile,((i%5)*size,(i//5)*size))
    return sheet
