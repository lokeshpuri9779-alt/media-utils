"""Explicit opt-in durable archive for reviewed-preview artwork packages.

Archives immutable PNG bytes; never marks artwork approved or publishes videos.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from astra.asset_package_qa import audit


def archive(manifest_path, store):
    manifest = Path(manifest_path)
    quality = audit(manifest)
    if not quality["ready_for_visual_review"]:
        raise ValueError("artwork_package_failed_quality_gate")
    rows = json.loads(manifest.read_text(encoding="utf-8"))["assets"]
    root = manifest.parent.parent.resolve()
    records = []
    for row in rows:
        source = (root / row["path"]).resolve()
        if root not in source.parents:
            raise ValueError("unsafe_artwork_path")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if row.get("sha256") and row["sha256"] != digest:
            raise ValueError("artwork_digest_mismatch")
        receipt = store.put(source)
        if receipt.get("sha256") != digest:
            raise ValueError("archive_receipt_digest_mismatch")
        if store.verify(receipt) is False:
            raise ValueError("archive_verification_failed")
        records.append({"id": row["id"], "status": "pending_review",
                        "category": row["category"], "tags": row.get("tags", []),
                        "story_content_id": row.get("story_content_id"),
                        "scene_id": row.get("scene_id"),
                        "source_status": row.get("status"),
                        "artifact": receipt})
    return {"schema": "astra.artwork.archive.v1", "assets": records,
            "approved": 0, "archived": len(records)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    from astra_v2.adaptive_remote_store import store_from_environment
    store = store_from_environment(Path(args.receipt).parent / ".cache")
    result = archive(args.manifest, store)
    destination = Path(args.receipt)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"archived": result["archived"], "approved": 0}))


if __name__ == "__main__":
    main()
