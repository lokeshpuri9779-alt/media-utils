"""Bounded editorial packet for seven-scene performance Shorts.

This packet is review-only. It cannot approve, render, schedule, or publish.
"""
from __future__ import annotations

import hashlib
import json

from astra_v2.performance_short_contract import validate_short_outline


def build_packet(candidates):
    if not isinstance(candidates, list):
        raise ValueError("candidates_must_be_list")
    seen = set()
    items = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("invalid_candidate")
        cid = candidate.get("content_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ValueError("candidate_identity_missing_or_duplicate")
        seen.add(cid)
        if (candidate.get("kind") != "performance_short_candidate"
                or candidate.get("format_profile") != "shorts_v2_7scene"
                or candidate.get("production_ready") is not False
                or candidate.get("approved") is not False
                or candidate.get("eligible_for_automatic_publishing") is not False
                or candidate.get("published") is not False):
            raise ValueError("candidate_must_remain_unapproved_and_unpublished")
        outline = {
            "premise": candidate.get("premise"),
            "character_bible": candidate.get("character_bible"),
            "scenes": candidate.get("performance_scenes"),
            "scorecard": candidate.get("performance_scorecard"),
            "hard_failures": candidate.get("hard_failures", []),
        }
        validation = validate_short_outline(outline)
        if not validation["valid"]:
            raise ValueError("candidate_failed_performance_contract")
        if candidate.get("plot_fingerprint") != validation["premise_fingerprint"]:
            raise ValueError("candidate_plot_fingerprint_mismatch")
        source_hash = hashlib.sha256(json.dumps(
            candidate, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        items.append({
            "candidate_id": cid,
            "source_sha256": source_hash,
            "title": candidate.get("title"),
            "question": candidate.get("question"),
            "answer": candidate.get("answer"),
            "premise": candidate["premise"],
            "character_bible": candidate["character_bible"],
            "story_cast": candidate.get("story_cast"),
            "performance_scenes": candidate["performance_scenes"],
            "story_beats": candidate.get("story_beats"),
            "scorecard": candidate["performance_scorecard"],
            "validation": validation,
            "decision": "not_approved",
            "required_next_action": "human_editorial_review_and_visual_proof",
            "production_ready": False,
            "eligible_for_automatic_publishing": False,
        })
    return {
        "schema_version": 2,
        "format_profile": "shorts_v2_7scene",
        "count": len(items),
        "approved_count": 0,
        "rendering_triggered": False,
        "publication_triggered": False,
        "candidates": items,
    }
