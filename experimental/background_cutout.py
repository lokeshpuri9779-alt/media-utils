"""Conservative edge-connected solid-background removal for imported artwork.

Works only for nearly uniform corner backgrounds. Complex scenes require
human-approved masks; never erase interiors based on global color matching.
"""
from collections import deque
from PIL import Image

def remove_solid_background(image, tolerance=24, max_corner_spread=35):
    if not 0<=tolerance<=80: raise ValueError("invalid tolerance")
    rgba=image.convert("RGBA")
    w,h=rgba.size
    if w*h>16_000_000: raise ValueError("image too large")
    corners=[rgba.getpixel(p)[:3] for p in ((0,0),(w-1,0),(0,h-1),(w-1,h-1))]
    bg=tuple(round(sum(c[i] for c in corners)/4) for i in range(3))
    if any(max(abs(c[i]-bg[i]) for i in range(3))>max_corner_spread for c in corners):
        raise ValueError("nonuniform corners: supply a transparent cutout or manual mask")
    pixels=rgba.load()
    q=deque()
    seen=bytearray(w*h)
    for x in range(w):
        q.append((x,0));q.append((x,h-1))
    for y in range(h):
        q.append((0,y));q.append((w-1,y))
    removed=0
    while q:
        x,y=q.popleft()
        k=y*w+x
        if seen[k]:continue
        seen[k]=1
        r,g,b,a=pixels[x,y]
        if max(abs(r-bg[0]),abs(g-bg[1]),abs(b-bg[2]))>tolerance:continue
        pixels[x,y]=(r,g,b,0)
        removed+=1
        if x:q.append((x-1,y))
        if x+1<w:q.append((x+1,y))
        if y:q.append((x,y-1))
        if y+1<h:q.append((x,y+1))
    if removed<max(1,int(w*h*.01)):raise ValueError("no clear removable edge background")
    if removed>int(w*h*.98):raise ValueError("mask removed almost entire image")
    return rgba

def save_cutout(source,destination,tolerance=24):
    with Image.open(source) as im:
        result=remove_solid_background(im,tolerance=tolerance)
    result.save(destination)
    return destination
