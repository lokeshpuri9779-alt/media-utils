"""Read-only, deterministic cross-stage ASTRA production evidence ledger.

Evidence does not grant editorial approval or publishing eligibility.
"""
import argparse
import hashlib
import json
from pathlib import Path


def _read(path):
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def build_ledger(publisher_state, rewrite_queue, image_manifest):
    publisher = _read(publisher_state)
    queue = _read(rewrite_queue)
    manifest = _read(image_manifest)
    entries = {}
    for row in queue.get("rewrites", []):
        if not isinstance(row, dict):
            continue
        story = row.get("story")
        if not isinstance(story, dict):
            continue
        cid = story.get("content_id")
        if not isinstance(cid, str) or not cid.strip():
            continue
        entries[cid] = {"content_id": cid, "rewrite_status": row.get("status", "unknown"),
                        "image_hashes": [], "image_count": 0, "published": False}
    for asset in manifest.get("assets", []):
        if not isinstance(asset, dict):
            continue
        cid = asset.get("story_content_id")
        if not isinstance(cid, str) or cid not in entries:
            continue
        digest = asset.get("sha256")
        if (asset.get("status") in ("review_only", "cached_review_only")
                and isinstance(digest, str) and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest)):
            entries[cid]["image_hashes"].append(digest)
    published = publisher.get("published", {})
    if isinstance(published, dict):
        for cid, record in published.items():
            if not isinstance(cid, str):
                continue
            item = entries.setdefault(cid, {"content_id": cid, "image_hashes": [],
                                             "image_count": 0, "rewrite_status": "not_in_latest_queue",
                                             "published": False})
            item["published"] = True
            if isinstance(record, dict):
                item["youtube_video_id"] = record.get("video_id")
    for item in entries.values():
        item["image_hashes"] = sorted(set(item["image_hashes"]))
        item["image_count"] = len(item["image_hashes"])
        item["production_ready"] = False  # never infer approval from assets or journal
    rows = [entries[cid] for cid in sorted(entries)]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"schema_version": 1, "verification": "read_only_evidence_not_publisher_authorization",
            "record_count": len(rows), "ledger_sha256": hashlib.sha256(canonical).hexdigest(),
            "records": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publisher-state", required=True)
    parser.add_argument("--rewrite-queue", required=True)
    parser.add_argument("--image-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build_ledger(args.publisher_state, args.rewrite_queue, args.image_manifest)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_PRODUCTION_LEDGER=" + json.dumps({"record_count": result["record_count"],
          "ledger_sha256": result["ledger_sha256"], "production_approval_granted": False}))


if __name__ == "__main__":
    main()
