"""Validate independent, reviewed audiovisual QA attestations.

The QA registry must be obtained from a trusted, access-controlled review
source, not from the archived package or the producer's own metadata.
This verifier never generates or approves an attestation.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path


def _digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("invalid_qa_digest")
    return value


def qa_evidence_digest(record):
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_qa_claim(claim, candidate, video, registry_path):
    """Bind a reviewed verdict to the claimed approval and exact MP4 bytes."""
    if not isinstance(claim, dict) or not isinstance(candidate, dict):
        raise ValueError("invalid_qa_claim")
    path = Path(registry_path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("trusted_qa_registry_missing_or_invalid")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or registry.get("schema") != "astra.qa.registry.v1":
        raise ValueError("invalid_qa_registry_schema")
    entries = registry.get("reviews")
    if not isinstance(entries, list) or len(entries) > 10000:
        raise ValueError("invalid_qa_reviews")
    cid = claim.get("content_id")
    matching = [r for r in entries if isinstance(r, dict) and r.get("content_id") == cid]
    if len(matching) != 1:
        raise ValueError("qa_review_missing_or_ambiguous")
    review = matching[0]
    if (review.get("schema") != "astra.av.qa.v1"
            or review.get("decision") != "approve"
            or not isinstance(review.get("reviewer"), str)
            or not review["reviewer"].strip()
            or not isinstance(review.get("review_notes"), str)
            or not review["review_notes"].strip()):
        raise ValueError("qa_review_not_approved")
    if candidate.get("content_id") != cid or candidate.get("format") != "short":
        raise ValueError("qa_candidate_identity_mismatch")
    from astra_v2.adaptive_artifact_store import ArtifactStore
    video_digest = ArtifactStore.digest(Path(video))
    if (review.get("video_sha256") != _digest(video_digest)
            or candidate.get("sha256") != video_digest
            or review.get("approval_digest") != _digest(claim.get("approval_digest"))):
        raise ValueError("qa_evidence_package_mismatch")
    if qa_evidence_digest(review) != _digest(claim.get("qa_digest")):
        raise ValueError("qa_attestation_digest_mismatch")
    from astra_v2.creative import inspect_video
    inspect_video(Path(video), "short")
    return True
