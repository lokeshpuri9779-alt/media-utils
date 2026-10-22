"""Explicit, fail-closed bridge from independently approved scene art to renderer manifest.

Never converts Story Factory review-only evidence into an approval by itself.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from astra_v2.story_art_direction import illustration_requests


def build_approved_manifest(queue_path, image_manifest_path, decisions_path, asset_root, output_root):
    queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    images = json.loads(Path(image_manifest_path).read_text(encoding="utf-8"))
    decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    if not isinstance(decisions, dict) or decisions.get("schema_version") != 1:
        raise ValueError("Independent approval decisions required")
    approvals = decisions.get("approved_scenes")
    if not isinstance(approvals, list):
        raise ValueError("Missing independent scene decisions")
    root = Path(asset_root).resolve()
    destination = Path(output_root).resolve()
    entries = []
    staged = []
    stories = {row["story"]["content_id"]: row["story"] for row in queue.get("rewrites", [])
               if isinstance(row, dict) and row.get("status") == "awaiting_independent_editorial_approval"
               and isinstance(row.get("story"), dict) and isinstance(row["story"].get("content_id"), str)}
    by_key = {}
    for row in images.get("assets", []):
        if isinstance(row, dict):
            by_key.setdefault((row.get("story_content_id"), row.get("scene_id")), []).append(row)
    approved = {}
    for decision in approvals:
        if not isinstance(decision, dict) or decision.get("decision") != "approved":
            raise ValueError("Every supplied decision must be an explicit approval")
        cid, sid, digest = (decision.get("story_content_id"), decision.get("scene_id"),
                            decision.get("sha256"))
        if not isinstance(cid, str) or cid not in stories or not isinstance(sid, str):
            raise ValueError("Unknown story or scene approval")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid approved image digest")
        key = (cid, sid)
        if key in approved:
            raise ValueError("Duplicate scene approval")
        approved[key] = digest
    for cid, story in sorted(stories.items()):
        requests = illustration_requests(story)
        keys = [(cid, req["scene_id"]) for req in requests]
        if not all(key in approved for key in keys):
            continue
        for key, request in zip(keys, requests):
            matches = [row for row in by_key.get(key, []) if row.get("sha256") == approved[key]
                       and row.get("status") in ("review_only", "cached_review_only")
                       and row.get("story_visual_sha256") == request["story_visual_sha256"]]
            if len(matches) != 1:
                raise ValueError("Approved scene must match exactly one current visual plan asset")
            asset = matches[0]
            source = asset.get("path")
            if not isinstance(source, str):
                raise ValueError("Invalid source path")
            image_path = (root / source).resolve()
            if not image_path.is_relative_to(root) or not image_path.is_file():
                raise ValueError("Missing or unsafe approved image")
            raw = image_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != approved[key]:
                raise ValueError("Approved image bytes changed")
            from astra_v2.omniroute_image_assets import image_quality_report
            if not image_quality_report(raw, "scene")["passed"]:
                raise ValueError("Approved scene fails image quality validation")
            # Copy immutable approved bytes into the renderer's manifest root.
            # The manifest must live at output_root/art/manifest.json.
            target = destination / "art" / "assets" / "reviewed" / (approved[key] + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() != approved[key]:
                raise ValueError("Approved asset destination hash mismatch")
            staged.append((image_path, target, approved[key]))
            entries.append({"id": "reviewed-" + cid + "-" + key[1], "category": "background",
                            "status": "approved", "story_content_id": cid, "scene_id": key[1],
                            "sha256": approved[key], "path": str(target.relative_to(destination)),
                            "tags": [], "source": "independently-reviewed-story-factory"})
    # Only write files after every approved scene has passed validation.
    for source, target, digest in staged:
        if not target.is_file():
            shutil.copyfile(source, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("Staged renderer asset hash mismatch")
    return {"assets": entries}


def main():
    parser = argparse.ArgumentParser()
    for arg in ("queue", "images", "decisions", "asset-root", "output-root", "output"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    result = build_approved_manifest(args.queue, args.images, args.decisions,
                                     args.asset_root, args.output_root)
    target = Path(args.output)
    expected = Path(args.output_root).resolve() / "art" / "manifest.json"
    if target.resolve() != expected:
        raise ValueError("Renderer manifest must be output_root/art/manifest.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("ASTRA_APPROVED_ART_BRIDGE=" + json.dumps({"approved_scenes": len(result["assets"]),
                                                      "automatic_approvals": 0}))


if __name__ == "__main__":
    main()
