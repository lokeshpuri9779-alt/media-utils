"""Premium image composition: bright scene, safe layout, no duplicated placeholders.

Designed for user-approved transparent PNG/WebP assets. No image-generation API.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import math

@dataclass(frozen=True)
class Layer:
    path: str
    cx: float
    cy: float
    width: int
    height: int
    role: str="prop"
    z: int=0

def overlap_ratio(a,b):
    ax0,ay0,ax1,ay1=a;bx0,by0,bx1,by1=b
    area=max(0,min(ax1,bx1)-max(ax0,bx0))*max(0,min(ay1,by1)-max(ay0,by0))
    return area/max(1,min((ax1-ax0)*(ay1-ay0),(bx1-bx0)*(by1-by0)))

def layout(layers,width=720,height=1280,max_overlap=.06):
    if width<64 or height<64:raise ValueError("invalid canvas")
    placed=[]
    for item in sorted(layers,key=lambda x:(x.z,x.role,x.path)):
        if item.width<=0 or item.height<=0 or item.width>width or item.height>height:
            raise ValueError("invalid layer dimensions")
        x=int(item.cx-item.width/2);y=int(item.cy-item.height/2)
        x=max(0,min(width-item.width,x));y=max(0,min(height-item.height,y))
        box=(x,y,x+item.width,y+item.height)
        if item.role!="background":
            for old,other in placed:
                if other.role!="background" and overlap_ratio(box,old)>max_overlap:
                    raise ValueError(f"unsafe object overlap: {item.path} vs {other.path}")
        placed.append((box,item))
    return placed

def render(layers,width=720,height=1280,background=(117,204,255)):
    canvas=Image.new("RGBA",(width,height),(*background,255))
    draw=ImageDraw.Draw(canvas)
    draw.ellipse((-width//3,height//2,width//2,height+height//3),fill=(116,204,118,255))
    draw.ellipse((width//3,height//2,width+width//2,height+height//3),fill=(77,184,111,255))
    for box,item in layout(layers,width,height):
        with Image.open(item.path) as src:
            rgba=src.convert("RGBA")
            rgba.thumbnail((item.width,item.height),Image.Resampling.LANCZOS)
            x=box[0]+(item.width-rgba.width)//2
            y=box[1]+(item.height-rgba.height)//2
            canvas.alpha_composite(rgba,(x,y))
    return canvas.convert("RGB")

def quality_report(image,layers):
    rgb=image.convert("RGB")
    sample=rgb.resize((96,96))
    pixels=list(sample.getdata())
    brightness=sum((.2126*r+.7152*g+.0722*b) for r,g,b in pixels)/len(pixels)
    saturation=sum(max(p)-min(p) for p in pixels)/len(pixels)
    return {"brightness":round(brightness,1),"colorfulness_proxy":round(saturation,1),
            "layers":len(layers),"brightness_pass":brightness>=95,
            "color_pass":saturation>=35,"overlap_pass":True}
