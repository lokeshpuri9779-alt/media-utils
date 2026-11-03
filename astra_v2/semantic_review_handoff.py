"""Read-only, opt-in restoration of independently signed FULL-MP4 reviews.

The reviewer alone deposits packet.json and signed-review.json on the
dedicated astra-video-reviews branch. The producer/publisher NEVER creates
signatures or infers semantic approval from a render or contact sheet.
The existing semantic_video_gate still authenticates everything against the
candidate actually selected for upload, exact encoded MP4 and trusted key.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

from astra_v2.semantic_video_gate import _sha256_file, evaluate


REVIEW_BRANCH_REF = "refs/remotes/origin/astra-video-reviews"
REVIEW_REMOTE_REF = "refs/heads/astra-video-reviews"
MAX_PACKET_BYTES = 1024 * 1024
MAX_DECISION_BYTES = 64 * 1024


def _result(reason, *, packet_path=None, decision_path=None, verified=False):
    return {
        "status": "authenticated_review" if verified else "not_verified",
        "reason": reason,
        "verified": verified,
        "packet_path": str(packet_path) if verified else None,
        "decision_path": str(decision_path) if verified else None,
        "publication_approval": False,
        "publication_triggered": False,
    }


def _git(repo_dir, *args):
    # No shell, untrusted prompts, paths or credentials in commands/logs.
    return subprocess.run(
        ["git", *args], cwd=repo_dir, check=True, capture_output=True,
        timeout=25,
    ).stdout


def _review_blob(repo_dir, path, maximum):
    object_id = REVIEW_BRANCH_REF + ":" + path
    size = int(_git(repo_dir, "cat-file", "-s", object_id).strip())
    if not 0 < size <= maximum:
        raise ValueError("oversized_or_empty_signed_review")
    kind = _git(repo_dir, "cat-file", "-t", object_id).strip()
    if kind != b"blob":
        raise ValueError("review_document_not_blob")
    content = _git(repo_dir, "show", object_id)
    if len(content) != size:
        raise ValueError("review_document_size_changed")
    return content


def _write_private(path, data):
    # No overwrite, no secret material, avoid accidental reuse of a stale
    # packet from a previous candidate. Restrict runner-local permissions.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise


def restore_review(candidate, video_path, output_dir, public_key, *, repo_dir="."):
    """Locate signed files by content-id hash AND actual MP4 hash; fail closed.

    The reviewer branch is a transport, not an authority. Only an Ed25519
    decision accepted by the existing full-video gate is considered verified.
    """
    if not isinstance(candidate, dict) or candidate.get("genre") != "fiction":
        return _result("not_fiction")
    if candidate.get("format") != "short":
        return _result("not_short")
    content_id = candidate.get("content_id")
    if (not isinstance(content_id, str) or not 1 <= len(content_id) <= 256
            or not content_id.strip()):
        return _result("invalid_review_content_id")
    if not isinstance(public_key, str) or not public_key.strip():
        return _result("trusted_reviewer_public_key_unavailable")
    if not Path(video_path).is_file():
        return _result("source_media_unavailable")
    try:
        media_digest = _sha256_file(video_path)
        name_digest = hashlib.sha256(content_id.encode("utf-8")).hexdigest()
    except (OSError, ValueError, UnicodeError):
        return _result("source_media_unavailable")
    base = f"signed-reviews/{name_digest}/{media_digest}"
    try:
        _git(repo_dir, "fetch", "--no-tags", "--depth=1", "origin",
             REVIEW_REMOTE_REF + ":" + REVIEW_BRANCH_REF)
    except (OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired):
        return _result("review_branch_unavailable")
    try:
        packet = _review_blob(repo_dir, base + "/packet.json", MAX_PACKET_BYTES)
        decision = _review_blob(
            repo_dir, base + "/signed-review.json", MAX_DECISION_BYTES)
    except (OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired):
        return _result("matching_signed_review_missing_or_invalid")

    destination = Path(output_dir)
    packet_path = destination / "packet.json"
    decision_path = destination / "signed-review.json"
    try:
        destination.mkdir(mode=0o700, parents=True, exist_ok=False)
        _write_private(packet_path, packet)
        _write_private(decision_path, decision)
        verification = evaluate(
            candidate, video_path, packet_path=packet_path,
            review_path=decision_path, public_key=public_key)
        if verification["verified"] is True:
            return _result("independent_attestation_verified",
                           packet_path=packet_path, decision_path=decision_path,
                           verified=True)
        # Unsigned/untrusted/tampered submissions must not be left as a
        # plausible handoff for another review path or a later candidate.
        return _result(verification["reason"])
    except (OSError, ValueError, TypeError):
        return _result("review_restore_unavailable")
    finally:
        if packet_path.exists() or decision_path.exists():
            # On verified success, retain files for run.py's final re-check
            # before any YouTube reservation or transfer.
            if "verification" not in locals() or verification["verified"] is not True:
                packet_path.unlink(missing_ok=True)
                decision_path.unlink(missing_ok=True)
