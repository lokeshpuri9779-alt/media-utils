"""Bind an existing, encoded fiction episode to a REVIEW-ONLY visual packet.

This is a deterministic packaging step, not an AI/human visual assessment.
Only an independent complete-MP4 review can verify narrated actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image

from astra_v2.story_visual_review_packet import snapshot, write_packet

MAX_DECODED_PNG_BYTES = 15_000_000


def _decoded_frame_sha256(path):
    """Accept real 1080x1920 decoded PNGs, never arbitrary renamed files."""
    image = Path(path)
    if (not image.is_file() or image.is_symlink()
            or not 0 < image.stat().st_size <= MAX_DECODED_PNG_BYTES):
        raise ValueError("missing_or_oversized_actual_decoded_frame")
    try:
        with Image.open(image) as frame:
            if frame.format != "PNG" or frame.size != (1080, 1920):
                raise ValueError("invalid_actual_decoded_png")
            frame.verify()
    except (OSError, ValueError) as exc:
        raise ValueError("invalid_actual_decoded_png") from exc
    return _hash(image)


def _hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_episode_packet(story, report, receipt, *, video_path, sheet_path,
                          output_path, frames_dir=None):
    """Validate exact episode identities and expose a manual inspection packet.

    Never invent timestamps, write review decisions or claim semantic quality.
    """
    if (not isinstance(story, dict) or story.get("genre") != "fiction"
            or not isinstance(report, dict) or report.get("genre") != "fiction"
            or not isinstance(receipt, dict)):
        raise ValueError("fiction_evidence_required")
    beats = story.get("story_beats")
    scenes = report.get("scenes")
    if (not isinstance(beats, list) or len(beats) != 4
            or not isinstance(scenes, list) or len(scenes) != 4
            or receipt.get("shot_count") != 4
            or receipt.get("content_id") != story.get("content_id")):
        raise ValueError("four_beat_evidence_identity_mismatch")
    video_path, sheet_path, output_path = map(Path, (video_path, sheet_path, output_path))
    if output_path.exists():
        raise ValueError("review_packet_output_already_exists")
    if (not video_path.is_file() or video_path.stat().st_size == 0
            or not sheet_path.is_file() or sheet_path.stat().st_size == 0):
        raise ValueError("encoded_video_or_sheet_missing")
    media_hash = _hash(video_path)
    if media_hash != receipt.get("video_sha256"):
        raise ValueError("encoded_video_hash_mismatch")

    source = snapshot(story, scenes)
    if (not isinstance(source, dict) or source.get("status") != "captured"
            or not isinstance(source.get("beat_midpoint_times_seconds"), list)
            or len(source["beat_midpoint_times_seconds"]) != 4):
        raise ValueError("narration_midpoints_not_verified")
    times = source["beat_midpoint_times_seconds"]
    for scene, midpoint in zip(scenes, times):
        start, duration = scene.get("start"), scene.get("duration")
        if (type(start) not in (int, float) or type(duration) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(duration)
                or start < 0 or duration <= 0
                or not abs(midpoint - (start + duration / 2)) <= .001):
            raise ValueError("invalid_narration_sample_alignment")

    contact_manifest = {
        "source_mp4_sha256": media_hash,
        "contact_sheet_sha256": _hash(sheet_path),
        "sample_strategy": "planned_beat_midpoints",
        "sample_count": 4,
        "sample_times_seconds": times,
    }
    # Verify every existing sampled frame BEFORE writing a packet: otherwise
    # a missing sample could leave a partial review handoff.
    frame_rows = None
    if frames_dir is not None:
        root = Path(frames_dir)
        frame_rows = []
        for i, (scene, midpoint) in enumerate(zip(scenes, times), 1):
            images = {}
            for label, filename in (
                ("midpoint", f"decoded-beat-{i:02d}.png"),
                ("early", f"temporal-beat-{i:02d}-early.png"),
                ("late", f"temporal-beat-{i:02d}-late.png"),
            ):
                file = root / filename
                images[label] = {
                    "filename": filename,
                    "sha256": _decoded_frame_sha256(file),
                }
            # This compares storyboard and Studio METADATA, not any pixels.
            # Keep the generic motion label separate from the authored human
            # choreography so reviewers do not mistake "idle" for the script.
            action_context = source["beats"][i - 1]
            frame_rows.append({
                "beat": i, "narration_midpoint_seconds": midpoint,
                "planned_action": str(scene.get("story_human_action") or "")[:100],
                "generic_studio_action": action_context["planned_action"],
                "authored_human_action": action_context["authored_human_action"],
                "planned_human_action": action_context["planned_human_action"],
                "human_action_metadata_status": action_context["human_action_metadata_status"],
                "actual_decoded_frames": images,
                "narrated_action_visible": "not_verified",
                "character_and_prop_fidelity": "not_verified",
            })
    # Reuse the existing fail-closed reviewer packet format only after all
    # requested evidence files have been checked. It never grants approval.
    result = write_packet(source, receipt, contact_manifest, output_path,
                          contact_sheet_path=sheet_path)
    if frame_rows is not None:
        evidence = {
            "kind": "encoded_video_manual_scene_evidence_index",
            "video_sha256": media_hash,
            "story_sha256": source["story_sha256"],
            "contact_sheet_sha256": contact_manifest["contact_sheet_sha256"],
            "scenes": frame_rows,
            "semantic_quality": "not_verified",
            "independent_full_video_review_required": True,
            "publication_approval": False,
            "publication_triggered": False,
        }
        index_path = output_path.with_name("review-frame-index.json")
        if index_path.exists():
            raise ValueError("frame_index_already_exists")
        index_path.write_text(json.dumps(evidence, indent=2) + "\n",
                              encoding="utf-8")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description="Create a read-only encoded-episode review handoff")
    p.add_argument("--story", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--sheet", required=True)
    p.add_argument("--frames-dir", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    result = create_episode_packet(
        json.loads(Path(args.story).read_text(encoding="utf-8")),
        json.loads(Path(args.report).read_text(encoding="utf-8")),
        json.loads(Path(args.receipt).read_text(encoding="utf-8")),
        video_path=args.video, sheet_path=args.sheet,
        frames_dir=args.frames_dir, output_path=args.output)
    print("ASTRA_REVIEW_ONLY_EPISODE_PACKET=" + json.dumps({
        "story_sha256": result["story_sha256"],
        "source_mp4_sha256": result["source_mp4_sha256"],
        "review_status": result["review_status"],
        "publication_approval": False,
    }))


if __name__ == "__main__":
    main()
