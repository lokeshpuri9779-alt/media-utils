"""Offline bridge from existing reviewed stories to the adaptive warehouse.

This module never publishes or creates editorial approval. History must be
supplied by the caller from both publisher state and story history.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from astra_v2.editorial_approval_manifest import validate_manifest, story_digest
from astra_v2.adaptive_warehouse import Warehouse


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def register_reviewed(stories, reviews, history, warehouse: Warehouse):
    if history is None:
        raise ValueError("complete_publication_history_required")
    audit = validate_manifest(stories, reviews, history)
    by_id = {record["content_id"]: record for record in reviews}
    accepted = []
    rejected = []
    for story, result in zip(stories, audit["results"]):
        cid = result["content_id"]
        if not result["approved"]:
            rejected.append({"content_id": cid, "issues": result["issues"]})
            continue
        review = by_id[cid]
        warehouse.register(cid, story_sha256=story_digest(story),
                           reviewer=review["reviewer"],
                           review_sha256=digest(review),
                           dependencies={"story": story_digest(story)})
        accepted.append(cid)
    return {"registered": accepted, "rejected": rejected,
            "publication_triggered": False}
