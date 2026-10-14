"""Deterministic offline production manifest and continuity checks."""
import hashlib
import json
from pathlib import Path


def create_manifest(plan, output, seconds_per_scene=2):
    if plan.get("publication_allowed") is not False:
        raise ValueError("offline-only production manifest")
    scenes = plan.get("scenes", [])
    if not scenes:
        raise ValueError("no scenes")
    continuity = []
    previous_cast = None
    for index, scene in enumerate(scenes):
        if not scene.get("caption") or not scene.get("action"):
            raise ValueError(f"scene {index} missing caption or action")
        if scene.get("location") != plan.get("location"):
            raise ValueError(f"scene {index} has inconsistent location")
        cast = [a.get("character_id") for a in scene.get("actors", [])]
        if previous_cast is not None and cast != previous_cast:
            raise ValueError(f"scene {index} has inconsistent cast")
        previous_cast = cast
        continuity.append({
            "scene": index + 1,
            "start_seconds": index * seconds_per_scene,
            "end_seconds": (index + 1) * seconds_per_scene,
            "action": scene["action"],
            "location": scene["location"],
            "caption": scene["caption"],
            "cast": cast,
        })
    output = Path(output)
    assets = {}
    for filename in ("preview.mp4", "captions.srt", "soundtrack.wav",
                     "storyboard.png", "plan.json"):
        path = output / filename
        if not path.is_file():
            raise FileNotFoundError(f"missing production asset: {filename}")
        assets[filename] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifest = {
        "title": plan["title"],
        "episode": plan.get("episode", 1),
        "genre": plan["genre"],
        "location": plan["location"],
        "duration_seconds": len(scenes) * seconds_per_scene,
        "scenes": continuity,
        "assets": assets,
        "continuity_passed": True,
        "spoken_narration": False,
        "publication_allowed": False,
        "quality_approved": False,
    }
    (output / "production-manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
