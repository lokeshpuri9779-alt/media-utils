"""Opt-in, fail-closed placement of verified independent art into story frames.

No external downloads, no procedural recipes disguised as illustration files.
Storyboards explicitly select IDs and placement; an unknown ID rejects rendering.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from PIL import Image
from astra_v2.illustrated_asset_validation import validate_library

@lru_cache(maxsize=8)
def _verified(root):
    root=Path(root).resolve()
    report=validate_library(root)
    return {a["id"]:a for a in report["assets"]}

def apply_story_art(image, shot):
    """Composite explicitly requested verified art; do nothing if none requested."""
    requested=shot.get("illustrated_assets")
    if requested is None and shot.get("auto_illustrated_art"):
        from astra_v2.quality_asset_selector import select_or_request_generation
        root = Path(shot.get("illustrated_asset_root") or ".").resolve()
        tags = shot.get("auto_art_tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise ValueError("auto_art_tags must be a list of strings")
        video_format = "shorts" if image.height > image.width else "long"
        choice = select_or_request_generation(
            root, kind=shot.get("auto_art_kind", "prop"), tags=tags,
            style=shot.get("auto_art_style"), video_format=video_format,
            allow_attribution=False)
        if choice["needs_generation"]:
            return 0
        requested = [{"id": choice["asset"]["id"], "box": shot.get("auto_art_box")}]
    if requested is None:
        return 0
    if not isinstance(requested,list) or len(requested)>8:
        raise ValueError("illustrated_assets must be a list of up to eight placements")
    root=Path(shot.get("illustrated_asset_root") or ".").resolve()
    inventory=_verified(str(root))
    rendered=0
    for item in requested:
        if not isinstance(item,dict) or not isinstance(item.get("id"),str):
            raise ValueError("invalid illustrated asset placement")
        asset=inventory.get(item["id"])
        if asset is None:
            raise ValueError("illustrated asset not verified: "+item["id"])
        if asset["kind"] not in ("prop","pose","character","effect"):
            raise ValueError("only foreground artwork may be composited")
        bounds=item.get("box")
        if not (isinstance(bounds,list) and len(bounds)==4 and
                all(type(v) is int for v in bounds)):
            raise ValueError("illustrated asset requires integer [x,y,width,height]")
        x,y,w,h=bounds
        if w<1 or h<1 or x<0 or y<0 or x+w>image.width or y+h>image.height:
            raise ValueError("illustrated asset placement outside frame")
        with Image.open(root / asset["path"]) as original:
            artwork=original.convert("RGBA").resize((w,h),Image.Resampling.LANCZOS)
            image.paste(artwork,(x,y),artwork)
        rendered+=1
    return rendered
