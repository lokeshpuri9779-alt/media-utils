"""Import user-provided CC0 PNG packs into ASTRA's verified art inventory.

No unverified remote downloads; preserve attribution and source provenance.
Usage: python -m astra_v2.cc0_pack_importer --pack /path/to/unpacked/pack
    --source https://kenney.nl/assets/... --artist Kenney --kind prop
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from PIL import Image

KINDS = {"character","background","prop","pose","effect"}

def import_pack(pack, root, *, source, artist, kind="prop", max_files=3000):
    pack=Path(pack).resolve()
    root=Path(root).resolve()
    if not pack.is_dir() or not source or not artist or kind not in KINDS:
        raise ValueError("pack, source, artist and valid kind required")
    manifest=root/"art"/"manifest.json"
    manifest.parent.mkdir(parents=True,exist_ok=True)
    data=json.loads(manifest.read_text()) if manifest.exists() else {"assets":[]}
    entries=data["assets"]
    existing={e["id"] for e in entries}
    hashes=set()
    for e in entries:
        p=(root/e["path"]).resolve()
        if p.is_file():
            hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
    files=sorted(pack.rglob("*.png"))
    if len(files)>max_files:
        raise ValueError("pack exceeds max_files; split into batches")
    added=0
    for file in files:
        if file.is_symlink() or file.stat().st_size>16*1024*1024:
            continue
        raw=file.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        if digest in hashes:
            continue
        with Image.open(file) as im:
            im.verify()
        with Image.open(file) as im:
            if im.width<64 or im.height<64:
                continue
            if kind!="background" and im.mode not in ("RGBA","LA","P"):
                continue
        stem=re.sub(r"[^a-z0-9-]+","-",file.stem.lower()).strip("-")[:45] or "asset"
        asset_id=f"cc0-{stem}-{digest[:12]}"
        if asset_id in existing:
            continue
        relative=f"art/imported/{asset_id}.png"
        dest=root/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(file,dest)
        entries.append({"id":asset_id,"path":relative,"kind":kind,
                        "license":"CC0-1.0","source":source,"artist":artist})
        hashes.add(digest)
        existing.add(asset_id)
        added+=1
    manifest.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    from astra_v2.illustrated_asset_validation import validate_library
    report=validate_library(root)
    return {"added":added,"total_verified":report["verified_files"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--pack",required=True)
    parser.add_argument("--root",default=".")
    parser.add_argument("--source",required=True)
    parser.add_argument("--artist",required=True)
    parser.add_argument("--kind",choices=sorted(KINDS),default="prop")
    args=parser.parse_args()
    print(json.dumps(import_pack(args.pack,args.root,source=args.source,
                                 artist=args.artist,kind=args.kind)))

if __name__=="__main__":
    main()
