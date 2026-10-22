"""Opt-in remote-reviewed artwork -> Studio MP4 preparation; never publishes."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from astra_v2.restore_reviewed_artwork import restore_reviewed_artwork


def prepare_video(story_path, receipt_path, decisions_path, output_root, output_mp4, store, *, runner=None):
    from astra_v2.reviewed_artwork_intake import validate_package
    validation = validate_package(story_path, receipt_path, decisions_path)
    root = Path(output_root).resolve()
    story = json.loads(Path(story_path).read_text(encoding="utf-8"))
    content_id = story.get("content_id")
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("story_content_id_required")
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    # A receipt can contain many stories, but this job may render exactly one.
    approved = [row for row in receipt.get("assets", [])
                if isinstance(row, dict) and isinstance(decisions.get(row.get("id")), dict)
                and decisions[row["id"]].get("approved") is True]
    if not approved or any(row.get("story_content_id") != content_id for row in approved):
        raise ValueError("reviewed_artwork_story_mismatch")
    if validation["story_content_id"] != content_id:
        raise ValueError("validated_story_identity_mismatch")
    result = restore_reviewed_artwork(receipt_path, decisions_path, root, store)
    manifest = Path(result["manifest"])
    rows = json.loads(manifest.read_text(encoding="utf-8"))["assets"]
    scenes = [row["scene_id"] for row in rows]
    if len(scenes) != len(set(scenes)):
        raise ValueError("duplicate_video_scene")
    # Validate complete coverage against the real Studio story planner, not guessed scene counts.
    from studio_renderer import make_plan
    expected = len(make_plan(dict(story)))
    if expected == 0 or sorted(scenes) != [f"{i:03d}" for i in range(1, expected + 1)]:
        raise ValueError("incomplete_reviewed_story_artwork")
    output = Path(output_mp4).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "studio_renderer.py"),
               "--preview", str(output), "--story-json", str(Path(story_path).resolve()),
               "--reviewed-art-manifest", str(manifest),
               "--stills-dir", str(root / "stills")]
    if runner is None:
        runner = subprocess.run
    runner(command, check=True, timeout=600)
    if not output.is_file() or output.stat().st_size == 0:
        raise ValueError("studio_video_missing")
    report_path = output.with_suffix(".json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rendered = report.get("scenes", [])
    if len(rendered) != expected or any(not shot.get("artwork_asset_id") for shot in rendered):
        raise ValueError("studio_video_artwork_binding_failed")
    return {"video": str(output), "manifest": str(manifest), "scenes": expected, "published": False}


def main():
    parser = argparse.ArgumentParser(description="Prepare reviewed artwork MP4; never publish")
    for name in ("story-json", "receipt", "decisions", "output-root", "output-mp4"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    from astra_v2.adaptive_remote_store import store_from_environment
    store = store_from_environment(Path(args.output_root) / ".artifact-cache")
    print(json.dumps(prepare_video(args.story_json, args.receipt, args.decisions,
                                   args.output_root, args.output_mp4, store), sort_keys=True))


if __name__ == "__main__":
    main()
