"""Claim and restore an already-approved warehouse package.

A claim is NOT upload permission: the publisher must independently enforce
its current editorial, duplicate, channel and YouTube checks. An ambiguous
outcome remains reserved for manual reconciliation; never automatically requeue.
"""
from __future__ import annotations
import json
import os
from pathlib import Path


def take(output, *, warehouse=None, archive=None):
    from astra_v2.adaptive_shared_queue import warehouse_from_environment
    from astra_v2.adaptive_package_archive import PackageArchive
    from astra_v2.adaptive_remote_store import store_from_environment

    warehouse = warehouse if warehouse is not None else warehouse_from_environment()
    archive = archive if archive is not None else PackageArchive(
        store_from_environment(os.getenv("ASTRA_ARTIFACT_CACHE", "storage/artifacts")))
    claim = warehouse.claim()
    if claim is None:
        return None
    output = Path(output)
    if output.exists():
        raise ValueError("warehouse_output_already_exists")
    destination = output.parent / ("warehouse-" + claim["content_id"])
    # Failure after claim deliberately leaves reservation unrequeued.
    archive.restore(claim["receipt"], destination)
    candidate = json.loads((destination / "candidate.json").read_text(encoding="utf-8"))
    if candidate.get("content_id") != claim["content_id"]:
        raise ValueError("warehouse_candidate_identity_mismatch")
    if candidate.get("format") != "short":
        raise ValueError("warehouse_shorts_only")
    if not claim.get("approval_digest") or not claim.get("qa_digest"):
        raise ValueError("warehouse_evidence_missing")
    from astra_v2.adaptive_artifact_store import ArtifactStore
    if ArtifactStore.digest(destination / "video.mp4") != candidate.get("sha256"):
        raise ValueError("warehouse_video_digest_mismatch")
    output.write_bytes((destination / "video.mp4").read_bytes())
    candidate["warehouse_claim"] = {
        "content_id": claim["content_id"], "lease_token": claim["lease_token"],
        "approval_digest": claim["approval_digest"], "qa_digest": claim["qa_digest"]}
    return candidate
