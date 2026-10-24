"""Deterministic quality-first selection across verified illustrated assets.

No provider-specific quotas or priority. Select only assets that match the
requested scene and meet licensing, resolution and style constraints.
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image
from astra_v2.illustrated_asset_validation import validate_library

def select_assets(root, *, kind, tags=(), style=None, min_size=128, limit=5,
                  allow_attribution=False, video_format=None):
    root=Path(root).resolve()
    report=validate_library(root)
    if not report["verified_files"]:
        return []
    manifest=json.loads((root/"art"/"manifest.json").read_text())
    verified={a["id"]:a for a in report["assets"]}
    if video_format not in (None, "shorts", "long"):
        raise ValueError("invalid video format")
    requested={str(tag).lower() for tag in tags}
    ranked=[]
    for entry in manifest["assets"]:
        if entry["id"] not in verified or entry["kind"]!=kind:
            continue
        if entry["license"] in ("CC-BY-3.0", "CC-BY-4.0") and not allow_attribution:
            continue
        if style and entry.get("style")!=style:
            continue
        art=verified[entry["id"]]
        width,height=art["dimensions"]
        if video_format == "shorts" and width >= height:
            continue
        if video_format == "long" and width <= height:
            continue
        if min(width,height)<min_size:
            continue
        labels={str(t).lower() for t in entry.get("tags",[])}
        labels.update(entry["id"].replace("-"," ").split())
        overlap=len(requested & labels)
        if requested and overlap==0:
            continue
        with Image.open(root/entry["path"]) as im:
            alpha=im.getchannel("A") if "A" in im.getbands() else None
            transparency=alpha is not None and alpha.getextrema()[0]<255
        if kind in ("character","prop","pose") and not transparency:
            continue
        score=(overlap*100)+(min(width,height)//128)*3+(15 if transparency else 0)
        ranked.append((score,entry["id"],entry))
    ranked.sort(key=lambda row:(-row[0],row[1]))
    return [{"id":entry["id"],"path":entry["path"],"score":score,
             "sha256":verified[entry["id"]]["sha256"],
             "license":entry["license"],"source":entry["source"],
             "artist":entry["artist"]} for score,_,entry in ranked[:max(0,limit)]]


def select_or_request_generation(root, *, kind, tags=(), video_format=None,
                                 style=None, min_size=128, allow_attribution=False):
    """Use verified existing artwork first; report a generation gap only if none fits.

    This is a pure planning step: never calls an external provider or approves art.
    The caller may generate only when needs_generation is true.
    """
    matches = select_assets(root, kind=kind, tags=tags, style=style,
                            min_size=min_size, limit=1,
                            allow_attribution=allow_attribution,
                            video_format=video_format)
    if matches:
        return {"source": "existing_asset", "asset": matches[0],
                "needs_generation": False}
    return {"source": "missing_asset", "asset": None,
            "needs_generation": True}
