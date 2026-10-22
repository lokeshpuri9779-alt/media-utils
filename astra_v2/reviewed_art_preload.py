"""Fail-closed, opt-in reviewed artwork preload setup.

No scene art is promoted without an independently authored decision file.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

from astra_v2.reviewed_art_bridge import build_approved_manifest


def prepare_artwork(queue, images, decisions, asset_root, output_root):
    root = Path(output_root).resolve()
    manifest = root / "art" / "manifest.json"
    existing = {"assets": []}
    if manifest.exists():
        try:
            existing = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Existing renderer manifest invalid") from exc
        if not isinstance(existing, dict) or not isinstance(existing.get("assets"), list):
            raise ValueError("Existing renderer manifest invalid")
    result = build_approved_manifest(queue, images, decisions, asset_root, root)
    if not result["assets"]:
        raise ValueError("No complete independently approved illustration set")
    merged = list(existing["assets"])
    ids = {row.get("id") for row in merged if isinstance(row, dict)}
    keys = {(row.get("story_content_id"), row.get("scene_id"))
            for row in merged if isinstance(row, dict) and row.get("story_content_id")}
    for asset in result["assets"]:
        key = (asset["story_content_id"], asset["scene_id"])
        if asset["id"] in ids or key in keys:
            raise ValueError("Existing reviewed artwork identity conflict")
        merged.append(asset)
        ids.add(asset["id"])
        keys.add(key)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=manifest.parent,
                                     prefix=".reviewed-art-", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump({"assets": merged}, handle, indent=2, sort_keys=True)
        handle.write("\n")
    try:
        os.replace(temporary, manifest)
    finally:
        temporary.unlink(missing_ok=True)
    return len(result["assets"])

def main():
    parser = argparse.ArgumentParser()
    for name in ("queue", "images", "decisions", "asset-root", "output-root"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    count = prepare_artwork(args.queue, args.images, args.decisions,
                            args.asset_root, args.output_root)
    print("ASTRA_REVIEWED_ART_PRELOAD=" + json.dumps({"approved_scene_files": count,
         "publication_triggered": False, "renderer_execution_triggered": False}))


if __name__ == "__main__":
    main()
