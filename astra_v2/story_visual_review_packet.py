"""Offline, inspection-only storyboard-to-MP4 review packet for ASTRA fiction.

Four decoded frame samples do not prove that any narrated event occurred.
The packet binds a storyboard snapshot, asset compositor receipt and sampled
video to the same encoded MP4 SHA256. It never grants publication approval.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

MAX_BEATS = 24
MAX_SHOTS = 48
MAX_FIELD_CHARS = 600


def _text(value):
    return value.strip()[:MAX_FIELD_CHARS] if isinstance(value, str) else ""


def snapshot(story, plan=None):
    """Capture an immutable, bounded visual checklist before video encoding."""
    if not isinstance(story, dict) or story.get("genre") != "fiction":
        return None
    beats = story.get("story_beats")
    if not isinstance(beats, list) or len(beats) > MAX_BEATS:
        return {"status": "invalid_storyboard", "content_id": _text(story.get("content_id"))}
    from astra_v2.editorial_approval_manifest import story_digest
    try:
        digest = story_digest(story)
    except (TypeError, ValueError, OverflowError):
        return {"status": "invalid_storyboard", "content_id": _text(story.get("content_id"))}

    plan = plan if isinstance(plan, (list, tuple)) and len(plan) <= MAX_SHOTS else []
    expected = []
    for i, beat in enumerate(beats, 1):
        if not isinstance(beat, dict):
            return {"status": "invalid_storyboard", "content_id": _text(story.get("content_id"))}
        shot = plan[i - 1] if i <= len(plan) and isinstance(plan[i - 1], dict) else {}
        expected.append({
            "beat": i,
            "speech": _text(beat.get("speech")),
            "visual_prompt": _text(beat.get("visual_prompt") or beat.get("visual")),
            "story_beat": _text(beat.get("story_beat")),
            "planned_visual": _text(shot.get("visual") or beat.get("visual")),
            "planned_subject": _text(shot.get("story_subject")),
            "planned_action": _text(shot.get("story_action")),
            "planned_environment": _text(shot.get("story_environment")),
        })
    return {
        "status": "captured" if expected else "invalid_storyboard",
        "content_id": _text(story.get("content_id")),
        "title": _text(story.get("title")),
        "story_sha256": digest,
        "beats": expected,
        "planned_shots": len(plan),
    }


def build_packet(source, asset_receipt, contact_manifest):
    """Validate evidence identities; the only review decision is unverified."""
    if not isinstance(source, dict) or source.get("status") != "captured":
        raise ValueError("storyboard_snapshot_unavailable")
    if not isinstance(asset_receipt, dict) or not isinstance(contact_manifest, dict):
        raise ValueError("visual_evidence_missing")
    digest = asset_receipt.get("video_sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
            or digest != contact_manifest.get("source_mp4_sha256")):
        raise ValueError("encoded_video_hash_mismatch")
    sheet_digest = contact_manifest.get("contact_sheet_sha256")
    if (not isinstance(sheet_digest, str) or len(sheet_digest) != 64
            or any(c not in "0123456789abcdef" for c in sheet_digest)):
        raise ValueError("contact_sheet_hash_missing")
    if source["content_id"] != asset_receipt.get("content_id"):
        raise ValueError("story_asset_identity_mismatch")
    shot_count = asset_receipt.get("shot_count")
    shots = asset_receipt.get("shots")
    if (type(shot_count) is not int or not 1 <= shot_count <= MAX_SHOTS
            or not isinstance(shots, list) or len(shots) != shot_count):
        raise ValueError("invalid_asset_shot_receipt")
    count = contact_manifest.get("sample_count")
    times = contact_manifest.get("sample_times_seconds")
    if (type(count) is not int or count != 4 or not isinstance(times, list)
            or len(times) != count or any(
                type(t) not in (float, int) or not math.isfinite(t) or t < 0
                for t in times) or list(times) != sorted(times)
            or len(set(times)) != count):
        raise ValueError("invalid_decoded_frame_samples")

    # A four-frame uniform sample is NOT guaranteed to align with four story
    # shots, even when both happen to have the same count.
    rows = []
    for beat in source["beats"]:
        i = beat["beat"]
        shot = shots[i-1] if len(source["beats"]) == shot_count else None
        rows.append({
            **beat,
            "asset_shot_status": (
                _text(shot.get("status")) if isinstance(shot, dict) else "not_aligned"
            ),
            "character_visible": "not_verified",
            "narrated_action_visible": "not_verified",
            "visual_prompt_matches_video": "not_verified",
            "setting_and_prop_continuity": "not_verified",
        })
    return {
        "schema_version": 1,
        "kind": "independent_story_vs_video_inspection_packet",
        "content_id": source["content_id"],
        "title": source["title"],
        "story_sha256": source["story_sha256"],
        "source_mp4_sha256": digest,
        "contact_sheet_sha256": sheet_digest,
        "story_beat_count": len(rows),
        "rendered_shot_count": shot_count,
        "frame_sample_count": count,
        "sample_times_seconds": times,
        "sample_alignment": "not_established",
        "review_status": "pending_independent_visual_inspection",
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "publication_triggered": False,
        "scope": (
            "Human-readable comparison of authored beats, Studio shot metadata, "
            "background compositor evidence, and four decoded MP4 samples. "
            "No automatic confirmation of characters, motion, or story fidelity."
        ),
        "beats": rows,
    }


def write_packet(source, asset_receipt, contact_manifest, output_path, *, contact_sheet_path):
    """Only write a packet when the actual contact JPEG matches its SHA256."""
    packet = build_packet(source, asset_receipt, contact_manifest)
    image = Path(contact_sheet_path)
    if not image.is_file() or image.stat().st_size == 0:
        raise ValueError("contact_sheet_missing")
    digest = hashlib.sha256()
    with image.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != packet["contact_sheet_sha256"]:
        raise ValueError("contact_sheet_hash_mismatch")
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Use the same directory as the already persisted contact sheet.
    dest.write_text(json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return {
        "path": str(dest),
        "content_id": packet["content_id"],
        "story_sha256": packet["story_sha256"],
        "source_mp4_sha256": packet["source_mp4_sha256"],
        "contact_sheet_sha256": packet["contact_sheet_sha256"],
        "story_beat_count": packet["story_beat_count"],
        "review_status": packet["review_status"],
        "publication_approval": False,
    }
