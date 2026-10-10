"""ASTRA Meta AI / Vibes handoff adapter (no unofficial API calls).

Creates per-scene prompts and imports user-exported clips for existing assembly.
Does not access cookies, scrape Meta, or trigger YouTube uploads.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def prepare(manifest: Path, output: Path) -> None:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("manifest requires a nonempty scenes list")
    output.mkdir(parents=True, exist_ok=True)
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or not isinstance(scene.get("prompt"), str) or not scene["prompt"].strip():
            raise ValueError(f"scene {index} needs a prompt")
        (output / f"scene_{index:03d}.txt").write_text(scene["prompt"].strip()+"\n", encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

def inspect_clips(folder: Path, count: int) -> dict:
    clips = sorted(folder.glob("scene_*.mp4"))
    expected = [f"scene_{i:03d}.mp4" for i in range(1, count+1)]
    actual = {p.name for p in clips if p.is_file() and p.stat().st_size > 0}
    return {"ready": all(n in actual for n in expected), "missing": [n for n in expected if n not in actual], "clips": [str(folder/n) for n in expected if n in actual]}

def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Meta AI prompts or validate exported clips")
    parser.add_argument("command", choices=["prepare", "check"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("meta_handoff"))
    parser.add_argument("--clips", type=Path, default=Path("meta_handoff/clips"))
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.command == "prepare":
        prepare(args.manifest, args.output)
        print(f"Prepared {len(data['scenes'])} prompts in {args.output}")
    else:
        print(json.dumps(inspect_clips(args.clips, len(data["scenes"])), indent=2))

if __name__ == "__main__":
    main()
