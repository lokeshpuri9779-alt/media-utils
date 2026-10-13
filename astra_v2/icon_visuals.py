"""Render cached, ISC-licensed Lucide SVG primitives without new dependencies."""
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path("asset_cache/lucide")
ALIASES={"fox":"dog","otter":"dog","owl":"bird","duck":"bird","firefly":"bug",
         "mouse":"rat","crab":"fish","ocean":"water","tree":"trees",
         "museum":"building","whale":"fish","robot":"bot","clock":"clock",
         "train":"tram-front","moon":"moon","book":"book-open","squirrel":"squirrel"}
def pick_icon(shot):
    from astra_v2.free_icon_cache import NAMES
    text=" ".join(str(shot.get(k) or "") for k in
                  ("visual_prompt","speech","headline","label")).lower()
    from astra_v2.story_visuals import SUBJECTS
    matches=[]
    for name,pattern in SUBJECTS:
        found=re.search(pattern,text)
        if found: matches.append((found.start(),ALIASES.get(name,name)))
    if matches:
        name=min(matches)[1]
        if name in NAMES: return name
    words=set(re.findall(r"[a-z]+(?:-[a-z]+)?",text))
    for name in NAMES:
        if name in words: return name
    return None

def overlay_icon(im,shot,t,accent):
    name=pick_icon(shot)
    if not name: return False
    file=ROOT/(name+".svg")
    if not file.is_file(): return False
    try:
        data=file.read_bytes()
        if len(data)>100000 or b"<!DOCTYPE" in data or b"<!ENTITY" in data: return False
        root=ET.fromstring(data)
        if root.tag.split("}")[-1]!="svg": return False
        layer=Image.new("RGBA",(420,420))
        draw=ImageDraw.Draw(layer)
        color=tuple(accent)+(220,)
        scale=15
        def xy(node,key):
            return float(node.attrib.get(key,"0"))*scale+30
        def points(raw):
            nums=[float(x) for x in re.findall(r"-?\d+(?:\.\d+)?",raw)]
            return [(nums[i]*scale+30,nums[i+1]*scale+30) for i in range(0,len(nums)-1,2)]
        rendered=0
        for node in root.iter():
            tag=node.tag.split("}")[-1]
            if tag=="line":
                draw.line((xy(node,"x1"),xy(node,"y1"),xy(node,"x2"),xy(node,"y2")),fill=color,width=10)
            elif tag in ("polyline","polygon"):
                pts=points(node.attrib.get("points",""))
                if len(pts)>1: draw.line(pts+([pts[0]] if tag=="polygon" else []),fill=color,width=10,joint="curve")
            elif tag=="circle":
                x,y,r=xy(node,"cx"),xy(node,"cy"),float(node.attrib.get("r","0"))*scale
                draw.ellipse((x-r,y-r,x+r,y+r),outline=color,width=10)
            elif tag=="rect":
                x,y,w,h=xy(node,"x"),xy(node,"y"),float(node.attrib.get("width","0"))*scale,float(node.attrib.get("height","0"))*scale
                draw.rounded_rectangle((x,y,x+w,y+h),radius=12,outline=color,width=10)
            else: continue
            rendered+=1
        if not rendered:
            # Lucide icons frequently use SVG paths. A clean visual fallback
            # is preferable to silently rendering nothing or inventing shapes.
            # The full path renderer can be enabled once tested independently.
            return False
        bob=int(9*math.sin(t*1.6))
        im.paste(layer,(330,670+bob),layer)
        return True
    except (OSError,ValueError,ET.ParseError,TypeError):
        return False
