"""Independent binding of a warehouse claim to reviewed editorial evidence.

This validates editorial identity only. It does not grant upload permission:
a separate trusted audiovisual QA attestation is still required.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from astra_v2.editorial_approval_manifest import story_digest, review_decision


def approval_evidence_digest(story, review):
    """Hash the complete story and review, including reviewer and decision."""
    payload = {"schema": "astra.editorial.evidence.v1",
               "story": story, "review": review}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_editorial_claim(claim, stories_path, reviews_path, *, eligible_ids):
    """Fail closed unless a claim matches an eligible, immutable review pair."""
    if not isinstance(claim, dict) or not isinstance(eligible_ids, (list, tuple, set)):
        raise ValueError("invalid_editorial_claim")
    cid = claim.get("content_id")
    if not isinstance(cid, str) or cid not in eligible_ids:
        raise ValueError("warehouse_story_not_editorially_approved")
    stories = json.loads(Path(stories_path).read_text(encoding="utf-8"))["stories"]
    reviews = json.loads(Path(reviews_path).read_text(encoding="utf-8"))["reviews"]
    matching_stories = [s for s in stories if isinstance(s, dict) and s.get("content_id") == cid]
    matching_reviews = [r for r in reviews if isinstance(r, dict) and r.get("content_id") == cid]
    if len(matching_stories) != 1 or len(matching_reviews) != 1:
        raise ValueError("warehouse_editorial_evidence_not_unique")
    story, review = matching_stories[0], matching_reviews[0]
    if review.get("story_sha256") != story_digest(story) or review_decision(story, review):
        raise ValueError("warehouse_editorial_review_invalid")
    expected = approval_evidence_digest(story, review)
    if claim.get("approval_digest") != expected:
        raise ValueError("warehouse_approval_digest_mismatch")
    return True
