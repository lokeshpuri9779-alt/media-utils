"""Non-authorizing scene asset readiness audit for ASTRA Story Factory."""
import argparse
import hashlib
import json
from pathlib import Path

from astra_v2.production_ledger import _read


def audit_assets(rewrite_queue, image_manifest, asset_root):
    queue = _read(rewrite_queue)
    manifest = _read(image_manifest)
    root = Path(asset_root).resolve()
    expected = {}
    for rewrite in queue.get("rewrites", []):
        if not isinstance(rewrite, dict) or rewrite.get("status") != "awaiting_independent_editorial_approval":
            continue
        story = rewrite.get("story")
        if not isinstance(story, dict):
            continue
        cid = story.get("content_id")
        if not isinstance(cid, str) or not cid:
            continue
        try:
            from astra_v2.story_art_direction import illustration_requests
            requests = illustration_requests(story)
        except (ValueError, TypeError, KeyError):
            expected[cid] = None
            continue
        expected[cid] = {str(item.get("scene_id")) for item in requests if isinstance(item, dict)}
    valid = {}
    reasons = {}
    for asset in manifest.get("assets", []):
        if not isinstance(asset, dict):
            continue
        cid = asset.get("story_content_id")
        if cid not in expected or expected[cid] is None:
            continue
        if asset.get("status") not in ("review_only", "cached_review_only"):
            continue
        scene_id = str(asset.get("scene_id"))
        if scene_id not in expected[cid]:
            continue
        digest = asset.get("sha256")
        path = asset.get("path")
        if not (isinstance(digest, str) and len(digest) == 64
                and all(ch in "0123456789abcdef" for ch in digest)
                and isinstance(path, str) and path):
            reasons[cid] = "invalid_asset_identity"
            continue
        location = (root / path).resolve()
        if not location.is_relative_to(root) or not location.is_file():
            reasons[cid] = "missing_asset_file"
            continue
        try:
            if hashlib.sha256(location.read_bytes()).hexdigest() != digest:
                reasons[cid] = "asset_hash_mismatch"
                continue
            from astra_v2.omniroute_image_assets import image_quality_report
            if not image_quality_report(location.read_bytes(), "scene")["passed"]:
                reasons[cid] = "pixel_quality_failed"
                continue
        except (OSError, ValueError, TypeError):
            reasons[cid] = "asset_validation_failed"
            continue
        valid.setdefault(cid, set()).add(scene_id)
    rows = []
    for cid in sorted(expected):
        scenes = expected[cid]
        matched = valid.get(cid, set())
        complete = scenes is not None and bool(scenes) and scenes <= matched
        rows.append({"content_id": cid, "expected_scenes": len(scenes) if scenes is not None else None,
                     "verified_scenes": len(matched), "asset_files_complete": complete,
                     "editorial_approval": False, "renderer_integration_verified": False,
                     "production_ready": False,
                     "reason": reasons.get(cid, "files_verified_review_only" if complete else "incomplete_scene_assets")})
    return {"schema_version": 1, "verification": "sha256_and_pixel_checks_not_semantic_or_editorial_approval",
            "stories_checked": len(rows), "file_complete": sum(x["asset_files_complete"] for x in rows),
            "stories": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrite-queue", required=True)
    parser.add_argument("--image-manifest", required=True)
    parser.add_argument("--asset-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = audit_assets(args.rewrite_queue, args.image_manifest, args.asset_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("ASTRA_ASSET_READINESS=" + json.dumps({"stories_checked": report["stories_checked"],
        "file_complete": report["file_complete"], "production_approval_granted": False}))


if __name__ == "__main__":
    main()
