"""Restore independently approved story-scene art from immutable archive receipts.

No approval is inferred from storage. Decisions must be supplied independently,
with matching SHA-256, story identity, scene identity and visual review results.
"""
import hashlib
import json
from pathlib import Path


def restore_reviewed_artwork(receipt_path, decisions_path, output_root, store):
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    if receipt.get("schema") != "astra.artwork.archive.v1" or not isinstance(receipt.get("assets"), list):
        raise ValueError("invalid_archive_receipt")
    if not isinstance(decisions, dict):
        raise ValueError("invalid_artwork_decisions")
    root = Path(output_root).resolve()
    selected = []
    seen = set()
    for row in receipt["assets"]:
        record = row.get("artifact")
        if not isinstance(record, dict):
            raise ValueError("missing_artifact_record")
        digest = record.get("sha256")
        decision = decisions.get(row.get("id"))
        if not isinstance(decision, dict) or decision.get("approved") is not True:
            continue
        if (decision.get("sha256") != digest or decision.get("semantic_match") is not True
                or decision.get("character_continuity") is not True):
            raise ValueError("artwork_review_identity_mismatch")
        story, scene = row.get("story_content_id"), row.get("scene_id")
        if (not isinstance(story, str) or not story or not isinstance(scene, str) or not scene
                or row.get("category") != "background"):
            raise ValueError("invalid_reviewed_scene_identity")
        identity = (story, scene)
        if identity in seen:
            raise ValueError("duplicate_reviewed_scene")
        seen.add(identity)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid_reviewed_digest")
        selected.append((row, record, digest))
    if not selected:
        raise ValueError("no_independently_reviewed_artwork")
    assets = []
    for row, record, digest in selected:
        verified_path = store.verify(record, refresh=True)
        if not verified_path:
            raise ValueError("remote_artwork_verification_failed")
        verified = Path(verified_path)
        raw = verified.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("restored_artwork_digest_mismatch")
        from astra_v2.omniroute_image_assets import image_quality_report
        if not image_quality_report(raw, "scene")["passed"]:
            raise ValueError("restored_artwork_quality_failed")
        destination = root / "art" / "restored" / (digest + ".png")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError("local_restored_artwork_corrupt")
        if not destination.exists():
            temporary = destination.with_suffix(".tmp")
            try:
                temporary.write_bytes(raw)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        assets.append({"id": row["id"], "path": destination.relative_to(root).as_posix(),
                       "category": "background", "tags": row.get("tags", []),
                       "status": "approved", "sha256": digest,
                       "story_content_id": row["story_content_id"], "scene_id": row["scene_id"]})
    manifest = root / "art" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = manifest.with_suffix(".json.tmp")
    try:
        temporary_manifest.write_text(json.dumps({"assets": assets}, indent=2) + "\n", encoding="utf-8")
        temporary_manifest.replace(manifest)
    finally:
        temporary_manifest.unlink(missing_ok=True)
    return {"manifest": str(manifest), "restored": len(assets)}

def main():
    """Explicit opt-in restoration for Studio's --reviewed-art-manifest input."""
    import argparse
    parser = argparse.ArgumentParser(description="Restore independently approved archived artwork")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    from astra_v2.adaptive_remote_store import store_from_environment
    store = store_from_environment(Path(args.output_root) / ".artifact-cache")
    result = restore_reviewed_artwork(args.receipt, args.decisions, args.output_root, store)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
