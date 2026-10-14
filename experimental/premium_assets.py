"""Import user-approved image assets into a deterministic, local premium library.

No network calls, paid APIs, automatic publishing, or production branch changes.
Usage: python -m experimental.premium_assets import ./my-image.png --name puppy --kind character
"""
from __future__ import annotations
import argparse,hashlib,json,re,shutil
from pathlib import Path
from PIL import Image
from experimental.background_cutout import remove_solid_background

KINDS=("character","prop","background")
MAX_BYTES=12*1024*1024
MAX_PIXELS=16_000_000

def import_asset(source,library="premium-assets",name=None,kind="prop",auto_cutout=False):
    source=Path(source)
    if kind not in KINDS: raise ValueError("unsupported kind")
    if not source.is_file() or source.suffix.lower() not in (".png",".webp"):
        raise ValueError("source must be an existing PNG or WebP")
    if source.stat().st_size>MAX_BYTES: raise ValueError("image exceeds 12 MiB")
    slug=re.sub(r"[^a-z0-9]+","-",str(name or source.stem).lower()).strip("-")
    if not slug: raise ValueError("empty asset name")
    with Image.open(source) as im:
        im.verify()
    with Image.open(source) as im:
        w,h=im.size
        if w*h>MAX_PIXELS or min(w,h)<64: raise ValueError("unsupported image dimensions")
        if kind in ("character","prop") and "A" not in im.getbands() and "transparency" not in im.info and not auto_cutout:
            raise ValueError("characters and props require transparency; use --auto-cutout for flat backgrounds")
        rgba=remove_solid_background(im) if auto_cutout and kind in ("character","prop") and "A" not in im.getbands() and "transparency" not in im.info else im.convert("RGBA")
        if kind in ("character","prop"):
            alpha=rgba.getchannel("A")
            if alpha.getextrema()==(255,255): raise ValueError("image has no transparent pixels")
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        dest=Path(library)/kind/(slug+"-"+digest[:12]+".png")
        dest.parent.mkdir(parents=True,exist_ok=True)
        rgba.save(dest,optimize=True)
    record={"name":slug,"kind":kind,"path":dest.as_posix(),"source_sha256":digest,
            "width":w,"height":h,"approved_for_production":False,
            "license_verified":False,"motion_rigged":False}
    sidecar=dest.with_suffix(".json")
    sidecar.write_text(json.dumps(record,indent=2)+"\n")
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["import"])
    p.add_argument("source")
    p.add_argument("--library",default="premium-assets")
    p.add_argument("--name")
    p.add_argument("--auto-cutout",action="store_true")
    p.add_argument("--kind",choices=KINDS,default="prop")
    a=p.parse_args()
    print(json.dumps(import_asset(a.source,a.library,a.name,a.kind,a.auto_cutout),indent=2))

if __name__=="__main__":main()
