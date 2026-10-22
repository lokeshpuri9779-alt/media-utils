"""Fail-closed, opt-in reviewed artwork preload setup.

No scene art is promoted without an independently authored decision file.
"""
import argparse
import json
from pathlib import Path

from astra_v2.reviewed_art_bridge import build_approved_manifest


def prepare_artwork(queue, images, decisions, asset_root, output_root):
    root = Path(output_root).resolve()
    manifest = root / "art" / "manifest.json"
    # Refuse to replace a pre-existing renderer asset manifest. A merge must
    # preserve existing approved assets and is deliberately not implicit.
    if manifest.exists():
        raise ValueError("Existing renderer manifest must not be overwritten")
    result = build_approved_manifest(queue, images, decisions, asset_root, root)
    if not result["assets"]:
        raise ValueError("No complete independently approved illustration set")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
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
