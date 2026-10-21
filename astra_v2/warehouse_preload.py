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

    # Check editorial readiness before claiming any durable reservation.
    from astra_v2.editorial_runway_diagnostic import editorial_runway
    runway = editorial_runway(
        os.getenv("ASTRA_EDITORIAL_STORIES_FILE", "editorial/reviewed_stories.json"),
        os.getenv("ASTRA_EDITORIAL_REVIEWS_FILE", "editorial/reviewed_decisions.json"),
        os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"),
        os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"))
    # Recheck the reviewed manifest against each queued claim once selected.
    # This must happen before restore and does not replace audiovisual QA.
    registry_path = os.getenv("ASTRA_TRUSTED_QA_REGISTRY")
    if not registry_path:
        raise RuntimeError("warehouse_trusted_qa_registry_not_configured")
    registry = Path(registry_path)
    if (not registry.is_file() or registry.is_symlink()
            or registry.stat().st_size > 4 * 1024 * 1024):
        raise RuntimeError("warehouse_trusted_qa_registry_unavailable")
    # A registry delivered by the same writable producer artifact store is
    # not an independent trust root. Deployment must enforce separation.
    if os.getenv("ASTRA_QA_REGISTRY_ACCESS_CONTROLLED") != "1":
        raise RuntimeError("warehouse_qa_registry_trust_not_established")
    # Filter claims to currently eligible editorial IDs, preventing an
    # unapproved oldest queue entry from blocking approved packages.
    eligible_ids = runway["eligible_ids"]
    warehouse = warehouse if warehouse is not None else warehouse_from_environment()
    archive = archive if archive is not None else PackageArchive(
        store_from_environment(os.getenv("ASTRA_ARTIFACT_CACHE", "storage/artifacts")))
    claim = warehouse.claim(lease_seconds=3600, eligible_ids=eligible_ids)
    if claim is None:
        return None
    # Do not consume a claim without independently verified editorial and QA
    # evidence. Until the trusted verifier is integrated, fail closed.
    from astra_v2.warehouse_editorial_evidence import verify_editorial_claim
    verify_editorial_claim(
        claim,
        os.getenv("ASTRA_EDITORIAL_STORIES_FILE", "editorial/reviewed_stories.json"),
        os.getenv("ASTRA_EDITORIAL_REVIEWS_FILE", "editorial/reviewed_decisions.json"),
        eligible_ids=runway["eligible_ids"])
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
    import re
    for field in ("approval_digest", "qa_digest"):
        if not re.fullmatch(r"[a-f0-9]{64}", str(claim.get(field, ""))):
            raise ValueError("warehouse_evidence_digest_invalid")
    from astra_v2.adaptive_artifact_store import ArtifactStore
    if ArtifactStore.digest(destination / "video.mp4") != candidate.get("sha256"):
        raise ValueError("warehouse_video_digest_mismatch")
    from astra_v2.warehouse_qa_evidence import verify_qa_claim
    verify_qa_claim(claim, candidate, destination / "video.mp4", registry)
    import shutil
    with (destination / "video.mp4").open("rb") as source, output.open("xb") as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)
    candidate["warehouse_claim"] = {
        "content_id": claim["content_id"], "lease_token": claim["lease_token"],
        "approval_digest": claim["approval_digest"], "qa_digest": claim["qa_digest"]}
    return candidate



def renew_before_upload(claim, *, warehouse=None):
    """Refuse to start a transfer if its fenced warehouse lease has expired.

    The publisher must call this immediately before YouTube upload. Ambiguous
    transfers are never requeued or retried by this helper.
    """
    if not isinstance(claim, dict) or not claim.get("content_id") or not claim.get("lease_token"):
        raise ValueError("invalid_warehouse_claim")
    if warehouse is None:
        from astra_v2.adaptive_shared_queue import warehouse_from_environment
        warehouse = warehouse_from_environment()
    return warehouse.renew(claim["content_id"], claim["lease_token"], lease_seconds=3600)


def confirm_publication(claim, video_id, status, *, warehouse=None):
    """Confirm only a verified public YouTube video while the lease is valid.

    A failed confirmation leaves the reservation untouched for reconciliation.
    """
    import hashlib
    import re
    if not isinstance(claim, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(video_id)):
        raise ValueError("invalid_publication_evidence")
    if (not isinstance(status, dict) or status.get("privacyStatus") != "public"
            or status.get("uploadStatus") != "processed"):
        raise ValueError("youtube_public_processing_not_verified")
    if warehouse is None:
        from astra_v2.adaptive_shared_queue import warehouse_from_environment
        warehouse = warehouse_from_environment()
    content_id = claim["content_id"]
    token = claim["lease_token"]
    digest = hashlib.sha256((content_id + ":" + video_id + ":public").encode()).hexdigest()
    return warehouse.confirm(content_id, token, video_id, confirmation_digest=digest)
