"""Scene-aware opt-in Pillow camera motion, preserving Studio story visuals.

Applies a small deterministic camera push to existing rendered frames.
No canned characters, props, or story states are substituted.
"""
from __future__ import annotations
import math
import os
from PIL import Image

def enabled() -> bool:
    return os.getenv("ASTRA_STUDIO_PILLOW_MOTION","0") == "1"

def camera_motion(frame: Image.Image, t: float, *, strength: float = 0.012) -> Image.Image:
    if not isinstance(frame,Image.Image):
        raise TypeError("Expected Pillow frame")
    if not math.isfinite(t) or not (0 <= strength <= 0.025):
        raise ValueError("Invalid motion parameters")
    if strength == 0:
        return frame
    if frame.width < 2 or frame.height < 2:
        return frame
    width,height=frame.size
    # Tiny zoom avoids revealing missing pixels; same content stays visible.
    phase=(1-math.cos(2*math.pi*(t % 7.0)/7.0))/2
    zoom=1+strength*phase
    new_size=(math.ceil(width*zoom),math.ceil(height*zoom))
    # Crop before resizing: only the final output pixels need interpolation.
    # Avoid scaling a larger-than-output intermediate frame.
    crop_w=width/zoom
    crop_h=height/zoom
    left=(width-crop_w)/2
    top=(height-crop_h)/2
    return frame.transform((width,height),Image.Transform.EXTENT,
                           (left,top,left+crop_w,top+crop_h),
                           resample=Image.Resampling.BILINEAR)
    #


def render_scene_frame(renderer,plan,t,genre,duration):
    frame=renderer(plan,t,genre,duration)
    if not enabled():
        return frame
    try:
        return camera_motion(frame,t)
    except (TypeError,ValueError,MemoryError):
        # Never replace a valid Studio frame with a canned scene.
        return frame
