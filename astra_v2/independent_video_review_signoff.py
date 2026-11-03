"""Offline handoff for a separately authorized human full-MP4 review.

This CLI cannot inspect pixels, grant editorial approval, or upload. It signs
only an explicitly completed, four-beat independent checklist bound to exact
story, encoded MP4, sampled contact sheet and review packet bytes. The private
Ed25519 key must be held by the reviewer outside ASTRA's producer workflows.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat

from astra_v2.semantic_video_gate import _canonical, _sha256_file, evaluate


CHECKS = (
    "character_visible", "narrated_action_visible",
    "visual_prompt_matches_video", "setting_and_prop_continuity",
)


def _bounded_json(path, max_bytes):
    source = Path(path)
    if not source.is_file() or not 0 < source.stat().st_size <= max_bytes:
        raise ValueError("missing_or_oversized_input")
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError("invalid_json_input") from exc


def sign_independent_review(*, candidate_path, packet_path, video_path,
                            contact_sheet_path, checklist_path,
                            private_key_path, trusted_public_key_path,
                            output_path, reviewer_id, confirm_full_video=False):
    """Sign a human review only after explicit affirmative per-beat observations.

    A caller cannot substitute a four-frame contact sheet for watching the
    whole video. Requiring a checkbox is an attestation, not evidence that the
    independent person really watched it; trust rests with their held key.
    """
    if confirm_full_video is not True:
        raise ValueError("explicit_full_video_review_confirmation_required")
    if (not isinstance(reviewer_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{3,100}", reviewer_id)):
        raise ValueError("invalid_independent_reviewer_identity")
    output = Path(output_path)
    if output.exists():
        raise ValueError("review_output_already_exists")

    candidate = _bounded_json(candidate_path, 1024 * 1024)
    packet = _bounded_json(packet_path, 1024 * 1024)
    checklist = _bounded_json(checklist_path, 16 * 1024)
    if (not isinstance(candidate, dict) or not isinstance(packet, dict)
            or candidate.get("genre") != "fiction"
            or candidate.get("format") != "short"
            or packet.get("kind") != "independent_story_vs_video_inspection_packet"
            or packet.get("review_status") != "pending_independent_visual_inspection"
            or packet.get("semantic_quality") != "not_verified"
            or packet.get("publication_approval") is not False):
        raise ValueError("review_source_not_eligible")
    if (not isinstance(checklist, dict)
            or set(checklist) != {"complete_video_reviewed", "beat_checks"}
            or checklist["complete_video_reviewed"] is not True):
        raise ValueError("complete_video_review_not_attested")
    checks = checklist["beat_checks"]
    if not isinstance(checks, list) or len(checks) != 4:
        raise ValueError("four_beat_review_required")
    for i, row in enumerate(checks, 1):
        if (not isinstance(row, dict)
                or set(row) != {"beat", *CHECKS}
                or type(row.get("beat")) is not int or row["beat"] != i
                or any(row[field] is not True for field in CHECKS)):
            raise ValueError("independent_beat_review_incomplete")

    if (packet.get("content_id") != candidate.get("content_id")
            or packet.get("title") != candidate.get("title")
            or packet.get("story_beat_count") != 4
            or packet.get("frame_sample_count") != 4
            or not isinstance(candidate.get("story_beats"), list)
            or len(candidate["story_beats"]) != 4):
        raise ValueError("review_story_identity_mismatch")
    video_hash = _sha256_file(video_path)
    sheet_hash = _sha256_file(contact_sheet_path)
    if (packet.get("source_mp4_sha256") != video_hash
            or packet.get("contact_sheet_sha256") != sheet_hash):
        raise ValueError("review_video_or_contact_sheet_hash_mismatch")

    secret = Path(private_key_path)
    if not secret.is_file() or not 0 < secret.stat().st_size <= 16384:
        raise ValueError("reviewer_private_key_unavailable")
    if os.name == "posix" and stat.S_IMODE(secret.stat().st_mode) & 0o077:
        raise ValueError("reviewer_private_key_permissions_not_private")

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        loaded = serialization.load_pem_private_key(secret.read_bytes(), password=None)
        if not isinstance(loaded, Ed25519PrivateKey):
            raise ValueError("reviewer_key_must_be_ed25519")
        derived = loaded.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        public_key = Path(trusted_public_key_path).read_text(encoding="ascii").strip()
        if base64.b64decode(public_key, validate=True) != derived:
            raise ValueError("reviewer_key_not_trusted")
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        raise ValueError("reviewer_key_invalid_or_untrusted") from exc

    record = {
        "schema_version": 1,
        "content_id": candidate["content_id"],
        "story_sha256": packet["story_sha256"],
        "source_mp4_sha256": video_hash,
        "contact_sheet_sha256": sheet_hash,
        "review_packet_sha256": _sha256_file(packet_path),
        "reviewer_id": reviewer_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "decision": "approve",
        "complete_video_reviewed": True,
        "beat_checks": checks,
    }
    signed = {
        "record": record,
        "signature_ed25519": base64.b64encode(
            loaded.sign(_canonical(record))).decode("ascii"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    # No overwrite; avoid accidentally replacing another human review.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(signed, sort_keys=True, indent=2) + "\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise

    verified = evaluate(candidate, video_path, packet_path=packet_path,
                        review_path=output, public_key=public_key)
    if not verified["verified"]:
        output.unlink(missing_ok=True)
        raise ValueError("review_signature_or_story_validation_failed")
    return {
        "status": "signed_independent_review",
        "content_id": candidate["content_id"],
        "video_sha256": video_hash,
        "reviewer_id": reviewer_id,
        "signature_verified": True,
        "publication_triggered": False,
        "publication_approval": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Sign a separately observed full ASTRA fiction MP4, offline")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--mp4", required=True)
    parser.add_argument("--contact-sheet", required=True)
    parser.add_argument("--checklist", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--trusted-public-key", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--confirm-full-video-reviewed", action="store_true")
    args = parser.parse_args(argv)
    outcome = sign_independent_review(
        candidate_path=args.candidate, packet_path=args.packet,
        video_path=args.mp4, contact_sheet_path=args.contact_sheet,
        checklist_path=args.checklist, private_key_path=args.private_key,
        trusted_public_key_path=args.trusted_public_key,
        output_path=args.output, reviewer_id=args.reviewer_id,
        confirm_full_video=args.confirm_full_video_reviewed,
    )
    print("ASTRA_SIGNED_VIDEO_REVIEW=" + json.dumps(outcome, sort_keys=True))


if __name__ == "__main__":
    main()
