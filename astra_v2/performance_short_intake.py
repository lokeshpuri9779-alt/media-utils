"""Idempotent, fail-closed persistence for human editorial review packets.

This is a review inbox only. It never changes approval, readiness, render or
publication flags and never invokes a provider.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import os


def merge_packets(existing, incoming):
    if not isinstance(existing, dict) or not isinstance(incoming, dict):
        raise ValueError("review_packet_must_be_object")
    if incoming.get("format_profile") != "shorts_v2_7scene":
        raise ValueError("unsupported_review_packet_profile")
    if incoming.get("approved_count") != 0 or incoming.get("rendering_triggered") is not False or incoming.get("publication_triggered") is not False:
        raise ValueError("incoming_packet_must_be_review_only")
    old_items = existing.get("candidates", [])
    new_items = incoming.get("candidates", [])
    if not isinstance(old_items, list) or not isinstance(new_items, list):
        raise ValueError("review_queue_candidates_must_be_lists")
    merged = []
    by_id = {}
    for item in old_items + new_items:
        if not isinstance(item, dict):
            raise ValueError("invalid_review_queue_item")
        cid, digest = item.get("candidate_id"), item.get("source_sha256")
        if not isinstance(cid, str) or not cid or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("review_queue_identity_or_hash_missing")
        if (item.get("approved") is not False or item.get("production_ready") is not False
                or item.get("eligible_for_automatic_publishing") is not False
                or item.get("published") is not False
                or item.get("decision") != "not_approved"):
            raise ValueError("review_queue_item_must_remain_unapproved")
        if cid in by_id:
            if by_id[cid] != digest:
                raise ValueError("candidate_id_source_hash_conflict")
            continue
        by_id[cid] = digest
        merged.append(item)
    return {
        "schema_version": 1,
        "format_profile": "shorts_v2_7scene",
        "count": len(merged),
        "approved_count": 0,
        "rendering_triggered": False,
        "publication_triggered": False,
        "candidates": merged,
    }


def persist_packet(path, incoming):
    target = Path(path)
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("existing_performance_review_queue_unreadable") from exc
    else:
        existing = {"candidates": []}
    result = merge_packets(existing, incoming)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=str(target.parent),
                                prefix=target.name + ".", suffix=".tmp",
                                delete=False) as handle:
            temp_name = handle.name
            json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write(chr(10))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--queue", required=True)
    args = parser.parse_args(argv)
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    result = persist_packet(args.queue, packet)
    print("ASTRA_PERFORMANCE_REVIEW_INTAKE=" + json.dumps({
        "count": result["count"], "approved_count": 0,
        "rendering_triggered": False, "publication_triggered": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
