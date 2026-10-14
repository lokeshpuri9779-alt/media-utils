"""Safe local asset manifest checks for ASTRA premium demos."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from PIL import Image

def validate_asset(path,metadata,kind):
    path=Path(path)
    if not path.is_file():raise ValueError("asset file missing")
    if not metadata.get("approved_for_production") or not metadata.get("license_verified"):
        raise ValueError("asset approval and license verification required")
    if metadata.get("kind")!=kind:raise ValueError("asset kind mismatch")
    if path.suffix.lower() not in (".png",".webp"):raise ValueError("unsupported asset format")
    if path.stat().st_size>12*1024*1024:raise ValueError("asset too large")
    expected=metadata.get("source_sha256")
    if not isinstance(expected,str) or len(expected)!=64:raise ValueError("source provenance missing")
    # Imported assets are normalized PNGs. Their encoded bytes differ from the
    # original source; retain the source hash as provenance, not a false file hash.
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        w,h=im.size
        if w*h>16_000_000 or min(w,h)<64:raise ValueError("invalid dimensions")
        if kind!="background":
            alpha=im.convert("RGBA").getchannel("A")
            if alpha.getextrema()==(255,255):raise ValueError("transparent cutout required")
    return True

def scan(library):
    root=Path(library)
    approved={k:[] for k in ("character","prop","background")}
    rejected=[]
    for kind in approved:
        for record in sorted((root/kind).glob("*.json")):
            try:
                meta=json.loads(record.read_text())
                path=record.with_suffix(".png")
                validate_asset(path,meta,kind)
                approved[kind].append(str(path))
            except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
                rejected.append({"record":str(record),"reason":str(exc)})
    return {"approved":approved,"rejected":rejected}
