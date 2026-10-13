"""Free, bounded, license-tracked icon cache for ASTRA.

Fetches individual Lucide SVGs (ISC license) on demand. Does not run network
requests during import and never downloads an unbounded repository archive.
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/"
LICENSE = "ISC"
SOURCE = "https://github.com/lucide-icons/lucide"
NAMES = (
    "cat","dog","bird","rabbit","fish","bug","snail","squirrel","rat",
    "paw-print","tree-pine","trees","flower","flower-2","leaf","sprout",
    "sun","moon","star","cloud","cloud-rain","cloud-lightning","snowflake",
    "waves","mountain","mountain-snow","tent","house","castle","building",
    "train","car","bus","bike","ship","plane","rocket","sailboat",
    "clock","alarm-clock","hourglass","calendar","map","map-pin","compass",
    "book","book-open","library","scroll","newspaper","mail","message-circle",
    "lightbulb","flashlight","lamp","flame","sparkles","wand-sparkles",
    "key","lock","door-open","shield","sword","crown","gem","gift",
    "heart","smile","frown","laugh","eye","ear","hand","footprints",
    "music","mic","camera","video","film","clapperboard","palette","brush",
    "gamepad-2","puzzle","trophy","medal","target","flag","check","x",
    "arrow-right","arrow-left","arrow-up","arrow-down","circle-help",
    "search","settings","wrench","hammer","pickaxe","construction",
    "coffee","apple","carrot","cake","pizza","utensils","cup-soda",
    "umbrella","backpack","shirt","glasses","hat-glasses","anchor",
    "binoculars","telescope","satellite","atom","flask-conical","bot",
)
def download_icons(cache_dir="asset_cache/lucide", names=NAMES, limit=120):
    root=Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    allowed=set(NAMES)
    manifest={}
    for name in list(dict.fromkeys(names))[:max(0,min(int(limit),len(NAMES)))]:
        if name not in allowed or not re.fullmatch(r"[a-z0-9-]+",name):
            continue
        dest=root/(name+".svg")
        try:
            if dest.exists():
                data=dest.read_bytes()
            else:
                request=urllib.request.Request(BASE+name+".svg",headers={"User-Agent":"ASTRA-asset-cache/1.0"})
                with urllib.request.urlopen(request,timeout=8) as response:
                    data=response.read(100_001)
                if len(data)>100_000 or b"<svg" not in data[:500] or b"</svg>" not in data:
                    raise ValueError("invalid or oversized SVG")
                dest.write_bytes(data)
            manifest[name]={"path":str(dest),"sha256":hashlib.sha256(data).hexdigest(),
                            "license":LICENSE,"source":SOURCE,"url":BASE+name+".svg"}
        except (OSError,ValueError) as exc:
            print("ASTRA_ICON_SKIP="+name+":"+str(exc)[:100])
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True))
    print("ASTRA_ICON_CACHE="+json.dumps({"available":len(manifest),"requested":min(len(NAMES),int(limit))}))
    return manifest

if __name__=="__main__":
    download_icons()
