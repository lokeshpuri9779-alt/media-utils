"""Authenticated, independent FULL-MP4 semantic review attestation.

Four decoded frames and compositor receipts are only evidence for inspection.
This module does not analyze pixels, approve story scripts, or publish a video.
The Ed25519 private signing key stays with the independent reviewer. The
producer and publisher receive only the non-secret public verification key.
"""
from __future__ import annotations

from datetime import datetime
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_BEAT_CRITERIA = (
    "character_visible",
    "narrated_action_visible",
    "visual_prompt_matches_video",
    "setting_and_prop_continuity",
)
_RECORD_KEYS = frozenset({
    "schema_version", "content_id", "story_sha256", "source_mp4_sha256",
    "contact_sheet_sha256", "review_packet_sha256", "reviewer_id",
    "reviewed_at", "decision", "complete_video_reviewed", "beat_checks",
})


def _result(code, verified=False):
    # Fixed codes only: never echo secrets, story contents or untrusted paths.
    return {"status": "authenticated_review" if verified else "not_verified",
            "verified": verified, "reason": code,
            "publication_approval": False, "publication_triggered": False}


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _read_json(path, *, limit):
    file = Path(path)
    if not file.is_file() or not 0 < file.stat().st_size <= limit:
        raise ValueError("missing_or_oversized_review_evidence")
    return json.loads(file.read_text(encoding="utf-8"))


def _plain_text(value, maximum=600):
    return value.strip()[:maximum] if isinstance(value, str) else ""


def _canonical(record):
    return json.dumps(record, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def evaluate(candidate, video_path, *, packet_path=None, review_path=None, public_key=None):
    """Authenticate a reviewed MP4 against the exact submitted candidate.

    No supplied evidence can elevate a four-frame sample into full-video
    review. A separately authorized human reviewer MUST personally check the
    whole video and sign one record bound to the packet and actual MP4 bytes.
    """
    if not isinstance(candidate, dict) or candidate.get("genre") != "fiction":
        return _result("not_fiction")
    if candidate.get("format") != "short":
        return _result("not_short")
    # The reviewer-operated branch is a transport for separately signed files,
    # NOT an approval source. Only attempt it under the already-existing strict
    # gate, never during ordinary scheduled publishing or an unsigned audit.
    # Explicit file paths take precedence; one missing path stays an error.
    if (not packet_path and not review_path
            and os.getenv("ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW", "0") == "1"):
        try:
            import tempfile
            from astra_v2.semantic_review_handoff import restore_review
            with tempfile.TemporaryDirectory(prefix="astra-signed-review-") as temp:
                result = restore_review(candidate, video_path, Path(temp) / "evidence",
                                        public_key)
                return _result(result["reason"], verified=result["verified"] is True)
        except (OSError, ValueError, TypeError, RuntimeError):
            return _result("review_handoff_unavailable")
    if not packet_path or not review_path:
        return _result("review_missing")
    if not isinstance(public_key, str) or not public_key.strip():
        return _result("trusted_reviewer_public_key_unavailable")
    try:
        packet = _read_json(packet_path, limit=1024 * 1024)
        document = _read_json(review_path, limit=64 * 1024)
    except (OSError, ValueError, TypeError, UnicodeError):
        return _result("review_evidence_unavailable")
    if not isinstance(packet, dict) or not isinstance(document, dict):
        return _result("review_schema_invalid")
    record = document.get("record")
    signature = document.get("signature_ed25519")
    if (set(document) != {"record", "signature_ed25519"}
            or not isinstance(record, dict)
            or set(record) != _RECORD_KEYS
            or not isinstance(signature, str)):
        return _result("review_schema_invalid")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        raw_key = base64.b64decode(public_key, validate=True)
        raw_signature = base64.b64decode(signature, validate=True)
        if len(raw_key) != 32 or len(raw_signature) != 64:
            return _result("review_signature_invalid")
        Ed25519PublicKey.from_public_bytes(raw_key).verify(
            raw_signature, _canonical(record))
    except (ValueError, TypeError, binascii.Error, InvalidSignature):
        return _result("review_signature_invalid")
    except ImportError:
        return _result("review_crypto_unavailable")
    if record.get("schema_version") != 1 or type(record["schema_version"]) is not int:
        return _result("review_schema_invalid")
    if (record.get("decision") != "approve"
            or record.get("complete_video_reviewed") is not True):
        return _result("full_video_review_not_approved")
    reviewer = record.get("reviewer_id")
    if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 120:
        return _result("reviewer_identity_missing")
    reviewed_at = record.get("reviewed_at")
    if not isinstance(reviewed_at, str):
        return _result("review_time_invalid")
    try:
        checked_at = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        if checked_at.tzinfo is None or checked_at.utcoffset() is None:
            return _result("review_time_invalid")
    except (ValueError, OverflowError):
        return _result("review_time_invalid")

    if (packet.get("kind") != "independent_story_vs_video_inspection_packet"
            or packet.get("schema_version") != 1
            or type(packet.get("schema_version")) is not int
            or packet.get("review_status") != "pending_independent_visual_inspection"
            or packet.get("semantic_quality") != "not_verified"
            or packet.get("publication_approval") is not False):
        return _result("review_packet_not_original")
    beats = packet.get("beats")
    authored = candidate.get("story_beats")
    if (not isinstance(beats, list) or not isinstance(authored, list)
            or len(beats) != len(authored) or len(beats) != 4
            or packet.get("story_beat_count") != 4
            or packet.get("frame_sample_count") != 4):
        return _result("storybeat_count_mismatch")
    if (record.get("content_id") != candidate.get("content_id")
            or record.get("content_id") != packet.get("content_id")
            or packet.get("title") != candidate.get("title")):
        return _result("review_candidate_mismatch")
    for index, (source, expected) in enumerate(zip(authored, beats), 1):
        if not isinstance(source, dict) or not isinstance(expected, dict):
            return _result("storybeat_payload_invalid")
        if (type(expected.get("beat")) is not int or expected["beat"] != index
                or expected.get("speech") != _plain_text(source.get("speech"))
                or expected.get("story_beat") != _plain_text(source.get("story_beat"))
                or expected.get("visual_prompt") != _plain_text(
                    source.get("visual_prompt") or source.get("visual"))):
            return _result("storybeat_payload_mismatch")

    for key in ("story_sha256", "source_mp4_sha256",
                "contact_sheet_sha256", "review_packet_sha256"):
        if not isinstance(record.get(key), str) or not _DIGEST.fullmatch(record[key]):
            return _result("review_digest_invalid")
    if (record["story_sha256"] != packet.get("story_sha256")
            or record["contact_sheet_sha256"] != packet.get("contact_sheet_sha256")):
        return _result("story_or_contact_sheet_hash_mismatch")
    try:
        packet_hash = _sha256_file(packet_path)
        video_hash = _sha256_file(video_path)
    except (OSError, ValueError, TypeError):
        return _result("source_media_unavailable")
    if (packet_hash != record["review_packet_sha256"]
            or video_hash != record["source_mp4_sha256"]
            or video_hash != packet.get("source_mp4_sha256")):
        return _result("source_media_or_packet_hash_mismatch")

    checks = record.get("beat_checks")
    if not isinstance(checks, list) or len(checks) != len(beats):
        return _result("visual_checks_incomplete")
    for index, row in enumerate(checks, 1):
        if (not isinstance(row, dict)
                or set(row) != set(_BEAT_CRITERIA) | {"beat"}
                or type(row.get("beat")) is not int or row["beat"] != index
                or any(row.get(field) is not True for field in _BEAT_CRITERIA)):
            return _result("visual_checks_incomplete")
    # An authenticated human attestation is not an automated pixel or
    # narrator-to-scene semantic classifier, nor publication authorization.
    return _result("independent_attestation_verified", verified=True)
