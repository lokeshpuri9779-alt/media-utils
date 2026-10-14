"""Batch scene composer: semantic item visuals, transformations and movement.

Experimental, no publishing integration. Renders independent deterministic frames
so GitHub workers can safely split batches without shared mutable state.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from PIL import Image, ImageDraw
from experimental.item_renderer import SUPPORTED, render_item
from experimental.world_renderer import draw_asset
from experimental.world_library import TAXONOMY

@dataclass(frozen=True)
class SceneObject:
    kind: str
    category: str
    x: float
    y: float
    size: int=96
    action: str="idle"
    phase: float=0.0

@dataclass(frozen=True)
class ScenePlan:
    objects: tuple[SceneObject,...]
    width: int=360
    height: int=640
    background: tuple[int,int,int]=(32,45,71)

SUPPORTED_ACTIONS=("idle","float","bounce","sway","spin","pulse","slide")

def compose(plan: ScenePlan, t: float) -> Image.Image:
    if plan.width<32 or plan.height<32: raise ValueError("invalid scene dimensions")
    if not math.isfinite(t): raise ValueError("time must be finite")
    canvas=Image.new("RGB",(plan.width,plan.height),plan.background)
    d=ImageDraw.Draw(canvas)
    horizon=int(plan.height*.8)
    d.rectangle((0,horizon,plan.width,plan.height),fill=(58,99,86))
    for obj in plan.objects:
        if obj.category not in TAXONOMY: raise ValueError("unknown asset category")
        if obj.action not in SUPPORTED_ACTIONS: raise ValueError("unknown action")
        if obj.size<32: raise ValueError("invalid asset size")
        tile=(render_item(obj.kind,obj.category,size=obj.size)
              if obj.kind in SUPPORTED else draw_asset(obj.category,obj.kind,size=obj.size))
        # White-ish prototype background becomes transparent so objects can overlap.
        pixels=tile.convert("RGBA")
        data=pixels.load()
        for yy in range(pixels.height):
            for xx in range(pixels.width):
                if data[xx,yy][:3]==(238,243,248):
                    data[xx,yy]=(0,0,0,0)
        phase=t*2+obj.phase
        x,y=obj.x,obj.y
        if obj.action=="float": y+=math.sin(phase)*14
        elif obj.action=="bounce": y-=abs(math.sin(phase*2))*26
        elif obj.action=="sway": x+=math.sin(phase)*12
        elif obj.action=="slide": x+=t*20
        elif obj.action=="pulse":
            scale=1+.12*math.sin(phase)
            pixels=pixels.resize((max(1,round(pixels.width*scale)),max(1,round(pixels.height*scale))),Image.Resampling.BICUBIC)
        elif obj.action=="spin": pixels=pixels.rotate((t*80+obj.phase*30)%360,expand=True,resample=Image.Resampling.BICUBIC)
        canvas.paste(pixels,(round(x-pixels.width/2),round(y-pixels.height/2)),pixels)
    return canvas

def sample_plan() -> ScenePlan:
    return ScenePlan(objects=(
        SceneObject("sun","nature",300,95,94,"pulse"),
        SceneObject("cloud","nature",92,145,108,"slide"),
        SceneObject("house","architecture",170,455,160,"idle"),
        SceneObject("flower","flora",52,545,72,"sway"),
        SceneObject("apple","food",278,532,68,"bounce"),
    ))
