"""Validate a complete independently reviewed archive package before remote I/O."""
import argparse
import json
from pathlib import Path


def validate_package(story_path, receipt_path, decisions_path):
    story = json.loads(Path(story_path).read_text(encoding="utf-8"))
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    content_id = story.get("content_id")
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("story_content_id_required")
    if receipt.get("schema") != "astra.artwork.archive.v1" or not isinstance(receipt.get("assets"), list):
        raise ValueError("invalid_archive_receipt")
    if not isinstance(decisions, dict):
        raise ValueError("invalid_review_decisions")
    from studio_renderer import make_plan
    count = len(make_plan(dict(story)))
    if not count:
        raise ValueError("story_has_no_scenes")
    selected = {}
    seen_asset_ids = set()
    receipt_asset_ids = set()
    for row in receipt["assets"]:
        if not isinstance(row, dict):
            raise ValueError("invalid_archive_row")
        asset_id = row.get("id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in seen_asset_ids:
            raise ValueError("duplicate_or_invalid_archive_asset_id")
        seen_asset_ids.add(asset_id)
        receipt_asset_ids.add(asset_id)
        decision = decisions.get(asset_id)
        if not isinstance(decision, dict) or decision.get("approved") is not True:
            continue
        record = row.get("artifact")
        if not isinstance(record, dict):
            raise ValueError("approved_artwork_missing_record")
        digest = record.get("sha256")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
                or decision.get("sha256") != digest
                or decision.get("semantic_match") is not True
                or decision.get("character_continuity") is not True):
            raise ValueError("invalid_independent_artwork_approval")
        scene = row.get("scene_id")
        if (row.get("story_content_id") != content_id or row.get("category") != "background"
                or not isinstance(scene, str) or scene in selected):
            raise ValueError("approved_artwork_identity_mismatch")
        selected[scene] = digest
    if any(not isinstance(asset_id, str) or asset_id not in receipt_asset_ids
           for asset_id, decision in decisions.items()
           if isinstance(decision, dict) and decision.get("approved") is True):
        raise ValueError("orphaned_artwork_approval")
    required = {f"{index:03d}" for index in range(1, count + 1)}
    if set(selected) != required:
        raise ValueError("incomplete_reviewed_artwork_package")
    return {"story_content_id": content_id, "scenes": count, "approved_assets": len(selected),
            "ready_for_remote_restore": True, "published": False}


def main():
    parser = argparse.ArgumentParser(description="Validate independently reviewed artwork package")
    for name in ("story-json", "receipt", "decisions"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(validate_package(args.story_json, args.receipt, args.decisions), sort_keys=True))


if __name__ == "__main__":
    main()
