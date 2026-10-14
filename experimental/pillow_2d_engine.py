"""Isolated Pillow 2D motion engine. Not connected to ASTRA publishing."""
from __future__ import annotations
import math
from dataclasses import dataclass
from PIL import Image, ImageDraw
from experimental.motion_profiles import evaluate

@dataclass(frozen=True)
class Settings:
    width: int = 360
    height: int = 640
    supersample: int = 2

def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t*t*(3-2*t)

def render(t: float, settings: Settings = Settings()) -> Image.Image:
    """Deterministic timeline: approach, pickup, celebration; never reset prop."""
    w,h,s = settings.width,settings.height,settings.supersample
    if min(w,h,s) < 1: raise ValueError("Dimensions and supersample must be positive")
    canvas = Image.new("RGB", (w*s,h*s), (24,35,60))
    d = ImageDraw.Draw(canvas)
    def point(x,y): return (round(x*s),round(y*s))
    def oval(a,b,c,e,color): d.ellipse((*point(a,b),*point(c,e)),fill=color)
    def line(a,b,color,width): d.line([point(*a),point(*b)],fill=color,width=round(width*s))
    sx,sy=w/360,h/640
    # Render in normalized coordinates then scale through coordinate wrapper.
    old_point=point
    def point(x,y): return old_point(x*sx,y*sy)
    for i in range(7):
        depth=.3+i*.1
        x=(i*97-t*14*depth)%500-70
        y=120+i*54
        oval(x-47,y-14,x+47,y+14,(37+i*3,53+i*3,79+i*3))
    d.rectangle((*point(0,515),*point(360,640)),fill=(44,85,73))
    motion=evaluate(t)
    x=80+130*motion.walk
    cycle=motion.stride
    y=390-motion.bob
    skin=(241,188,122)
    oval(x-43,516,x+43,528,(27,58,57))
    for side in (-1,1):
        hip=(x+side*17,y+66)
        knee=(x+side*19+cycle*side*14,y+103)
        foot=(x+side*21+cycle*side*21,515)
        line(hip,knee,(47,74,112),12)
        line(knee,foot,(47,74,112),11)
        line(foot,(foot[0]+side*11,515),(31,36,48),9)
    lift=motion.pickup
    bx=275*(1-lift)+(x+79)*lift
    by=493*(1-lift)+(y-5)*lift
    oval(bx-18,by-18,bx+18,by+18,(245,171,59))
    oval(x-38,y-34,x+38,y+77,(84,170,199))
    for side in (-1,1):
        shoulder=(x+side*29,y-8)
        hand=(x+52+27*lift,y+36-41*lift) if side==1 else (x-52,y+36+11*motion.left_arm)
        elbow=((shoulder[0]+hand[0])/2+side*7,(shoulder[1]+hand[1])/2+12)
        line(shoulder,elbow,skin,11)
        line(elbow,hand,skin,10)
        oval(hand[0]-6,hand[1]-6,hand[0]+6,hand[1]+6,skin)
    oval(x-36,y-107,x+36,y-34,skin)
    blink=motion.blink
    for side in (-1,1):
        ex=x+side*15
        if blink: line((ex-5,y-74),(ex+5,y-74),(34,39,48),2)
        else: oval(ex-3,y-78,ex+3,y-71,(34,39,48))
    d.arc((*point(x-13,y-67),*point(x+13,y-49)),0,180,fill=(113,56,52),width=max(1,2*s))
    if motion.celebration>0:
        for j in range(7):
            cx=(j*67+23)%360
            cy=120+(j*41)%170+8*math.sin(t*2+j)
            radius=3*motion.celebration
            oval(cx-radius,cy-radius,cx+radius,cy+radius,(248,210,101))
    return canvas.resize((w,h),Image.Resampling.LANCZOS)

def render_mp4(path: str, duration: float=7, fps: int=24, settings: Settings=Settings()) -> None:
    """Stream raw frames to ffmpeg; bounded memory, no intermediate PNG files."""
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    if duration<=0 or fps<=0: raise ValueError("duration and fps must be positive")
    command=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y","-f","rawvideo",
             "-pix_fmt","rgb24","-s",f"{settings.width}x{settings.height}",
             "-r",str(fps),"-i","-","-c:v","libx264","-preset","veryfast",
             "-pix_fmt","yuv420p","-movflags","+faststart",path]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for i in range(round(duration*fps)):
            proc.stdin.write(render(i/fps,settings).tobytes())
    finally:
        proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError("ffmpeg encoding failed")
