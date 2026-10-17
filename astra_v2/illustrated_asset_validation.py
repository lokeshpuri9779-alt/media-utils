"""Validate *actual* independently illustrated PNG files, not procedural recipes.

Manifest schema: {"assets":[{"id":"fox-wave-01","path":"art/fox-wave-01.png",
"kind":"character","license":"CC0-1.0","source":"https://...","artist":"..."}]}
The manifest must be placed at the repository root. Assets are resolved relative
to the repository root; no URLs are downloaded at render time.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

KINDS = frozenset(("character", "background", "prop", "pose", "effect"))
LICENSES = frozenset(("CC0-1.0", "CC-BY-4.0", "CC-BY-3.0", "public-domain", "original"))
MAX_BYTES = 16 * 1024 * 1024

def validate_library(root, manifest="art/manifest.json"):
    """Fail closed on absent art, duplicate content, unsafe paths or bad provenance."""
    from PIL import Image
    root = Path(root).resolve()
    manifest_path = (root / manifest).resolve()
    if not manifest_path.is_relative_to(root) or not manifest_path.is_file():
        raise ValueError("asset manifest missing or outside repository")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = data.get("assets")
    if not isinstance(entries, list):
        raise ValueError("assets must be a list")
    ids, hashes, verified = set(), set(), []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid asset entry")
        asset_id = entry.get("id")
        relpath = entry.get("path")
        if not isinstance(asset_id, str) or not asset_id or asset_id in ids:
            raise ValueError("missing or duplicate asset id")
        if not isinstance(relpath, str) or not relpath.startswith("art/"):
            raise ValueError("art must live in art/")
        file_path = (root / relpath).resolve()
        if not file_path.is_relative_to(root / "art") or file_path.suffix.lower() != ".png":
            raise ValueError("unsafe or non-PNG asset path")
        if not file_path.is_file() or file_path.stat().st_size > MAX_BYTES:
            raise ValueError("missing or oversized asset")
        if entry.get("kind") not in KINDS or entry.get("license") not in LICENSES:
            raise ValueError("unsupported asset kind or license")
        if entry.get("license") in ("CC-BY-3.0", "CC-BY-4.0") and not entry.get("artist"):\n            raise ValueError("attribution-required art needs credited artist")\n        if not entry.get("artist") or not entry.get("source"):
            raise ValueError("asset provenance required")
        raw = file_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest in hashes:
            raise ValueError("duplicate PNG bytes")
        with Image.open(file_path) as img:
            img.verify()
        with Image.open(file_path) as img:
            if img.format != "PNG" or img.width < 64 or img.height < 64:
                raise ValueError("invalid or too-small PNG")
            if entry["kind"] in ("character", "prop", "pose") and img.mode not in ("RGBA", "LA", "P"):
                raise ValueError("foreground art must support transparency")
            dimensions = [img.width, img.height]
        ids.add(asset_id)
        hashes.add(digest)
        verified.append({"id":asset_id,"kind":entry["kind"],
                         "path":relpath,"sha256":digest,"dimensions":dimensions})
    return {"verified_files":len(verified),"distinct_png_hashes":len(hashes),
            "procedural_recipes_counted":0,"assets":verified}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--manifest",default="art/manifest.json")
    parser.add_argument("--min-assets",type=int,default=0)
    args=parser.parse_args()
    result=validate_library(args.root,args.manifest)
    if result["verified_files"] < args.min_assets:
        raise SystemExit("insufficient verified illustrated assets")
    print(json.dumps(result,indent=2))

if __name__ == "__main__":
    main()
