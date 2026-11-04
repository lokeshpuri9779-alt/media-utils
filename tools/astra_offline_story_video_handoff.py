"""Independent, review-only storyboard-to-encoded-MP4 evidence for ASTRA #951.

Three assistant-authored reference scenes only. This is NOT autonomous story
generation, narrative understanding, cinematic review, or publishing approval.
All video frames are re-decoded from real H.264 files by FFmpeg, not accepted
from renderer-reported pixel scores. Unknown source stories fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageChops

SOURCE_SHA = "1a393b2234f03d927ededc11b1e25c2afaa9e37c"
SOURCE_PR = 951
STAGES = ("setup", "attempt", "setback", "payoff")
SIZE = (320, 180)
FRAMES_PER_STAGE = 12
FRAMES = 48
FRAME_BYTES = SIZE[0] * SIZE[1] * 3
ROI = (43, 30, 285, 154)

# Independently fixed from the current source-pinned authored reference pack.
# A changed story digest requires review of the new reference, not auto-learning.
STORIES = {
    "glasshouse-sunshade": ("b6b2bb189aa9f46528fd372ae86ae1133d65420a1b884429810d3ea46153867e", "mina_beetle"),
    "footbridge-ducklings": ("2f46612d67d8a60e4ef99e8426e678756ca6394d2cf3d576386528adea6671e0", "beaver_builder"),
    "moon-mirror-garden": ("ed34f064feb0dc9405646b39b6e3434a12f0df409b0d3eae78333d0ab980961b", "moth_keeper"),
}

# Independent narrowly-scoped pixel witnesses: (ROI, RGB, channel tolerance,
# max initial pixels, min final pixels). Caption bars excluded.
WITNESSES = {
    "glasshouse-sunshade": {
        "canopy_over_seedlings": ((125, 55, 205, 69), (50, 118, 128), 35, 20, 250),
        "shaded_seedlings": ((130, 105, 170, 118), (29, 92, 54), 20, 5, 30),
    },
    "footbridge-ducklings": {
        "plank_across_gap": ((125, 106, 205, 117), (147, 96, 65), 35, 20, 200),
        "ducklings_on_safe_bank": ((35, 85, 96, 111), (248, 220, 88), 35, 20, 80),
    },
    "moon-mirror-garden": {
        "beam_on_flowerbed": ((130, 96, 170, 122), (210, 199, 148), 35, 20, 100),
        "open_pink_petals": ((80, 95, 210, 122), (235, 163, 228), 35, 20, 100),
    },
}
# Independent encoded-H.264 material witnesses for the six authored repair
# gestures. Fixed ROIs are version-pinned to #951; these are NOT semantic tests.
# Format: stage -> (expected gesture, ROI, RGB, tolerance, minimum late pixels).
PHYSICAL_WITNESSES = {
    "glasshouse-sunshade": {
        "attempt": ("thin_cord_loops_pulley", (92, 34, 118, 59), (244, 195, 112), 40, 23),
        "payoff": ("braided_rope_knotted_to_frame", (273, 102, 310, 135), (239, 219, 160), 40, 32),
    },
    "footbridge-ducklings": {
        "setback": ("plank_retrieval_hook_visible", (89, 114, 132, 145), (196, 87, 42), 26, 48),
        "payoff": ("reed_binding_at_both_bridge_posts", (237, 83, 255, 116), (246, 226, 163), 38, 26),
    },
    "moon-mirror-garden": {
        "attempt": ("brass_handle_rotates", (251, 65, 264, 81), (246, 168, 90), 38, 28),
        "payoff": ("replacement_metal_clip_locks_mirror", (258, 59, 285, 94), (236, 235, 212), 38, 34),
    },
}

SAFETY = ("approved", "published", "production_ready")


def _closed(data):
    return isinstance(data, dict) and all(data.get(key) is False for key in SAFETY)


def validate_metadata(storyboard, video_report):
    """Enforce exact source-matched story identity before any video is decoded."""
    if (not _closed(storyboard) or not _closed(video_report)
            or storyboard.get("experiment") != "astra-offline-storyboards-v1"
            or video_report.get("experiment") != "astra-cpu-procedural-motion-proofs-v1"
            or storyboard.get("real_model_inference_executed") is not False
            or storyboard.get("frames_rendered") is not False
            or storyboard.get("semantic_fidelity") != "not_verified"
            or storyboard.get("manual_editorial_and_visual_review_required") is not True
            or video_report.get("model_inference_executed") is not False
            or video_report.get("human_visual_review_required") is not True
            or video_report.get("production_quality") != "not_verified"
            or video_report.get("decoded_mp4_physical_repair_cues_checked") is not True
            or video_report.get("video_count") != 3
            or storyboard.get("reference_count") != 3
            or storyboard.get("total_shots") != 12):
        raise ValueError("Source packet metadata does not meet review-only evidence contract")
    packets = storyboard.get("packets")
    previews = video_report.get("video_previews")
    if not isinstance(packets, list) or not isinstance(previews, list):
        raise ValueError("Missing source story or video proof list")
    if (len(packets) != 3 or len(previews) != 3
            or {p.get("case_id") for p in packets if isinstance(p, dict)} != set(STORIES)
            or {p.get("case_id") for p in previews if isinstance(p, dict)} != set(STORIES)):
        raise ValueError("Unknown, missing, swapped or duplicated story/video case IDs")
    story_by_id, video_by_id = {}, {}
    for item in packets:
        cid = item["case_id"]
        digest, actor = STORIES[cid]
        shots = item.get("shots")
        if (not _closed(item) or item.get("story_digest") != digest
                or item.get("character_id") != actor
                or item.get("shot_count") != 4
                or item.get("event_state_contract_valid") is not True
                or item.get("story_visual_semantics") != "not_verified"
                or item.get("source_status") != "assistant_drafted_reference_not_independently_reviewed"
                or not isinstance(shots, list) or len(shots) != 4):
            raise ValueError("Storyboard identity or causal ledger unavailable: " + cid)
        for i, shot in enumerate(shots):
            if (not isinstance(shot, dict) or shot.get("stage") != STAGES[i]
                    or shot.get("character_id") != actor
                    or shot.get("asset_verification") != "not_verified"
                    or shot.get("frame_generation_executed") is not False
                    or shot.get("manual_visual_review_required") is not True
                    or not isinstance(shot.get("source_beat"), str)
                    or len(shot["source_beat"].strip()) < 24
                    or shot.get("focus_state") not in (shot.get("after_state") or [])
                    or not isinstance(shot.get("before_state"), list)
                    or not isinstance(shot.get("after_state"), list)):
                raise ValueError("Storyboard beat is not a pinned visible-action plan: " + cid)
            if i and shots[i - 1]["after_state"] != shot["before_state"]:
                raise ValueError("Storyboard scene-state transition discontinuity: " + cid)
        story_by_id[cid] = item
    for item in previews:
        cid = item["case_id"]
        decoded = item.get("decoded_mp4_visual_cues") or {}
        actor = item.get("decoded_character_presence_cues") or {}
        if (not _closed(item) or item.get("review_only") is not True
                or item.get("file") != cid + ".mp4"
                or item.get("frame_count") != FRAMES
                or item.get("decoded_frame_count_verified") != FRAMES
                or item.get("fps") != 12 or item.get("dimensions") != list(SIZE)
                or item.get("codec") != "h264"
                or item.get("pixel_changes_verified") is not True
                or item.get("visible_story_outcome_cues_verified") is not True
                or item.get("story_semantic_accuracy") != "not_verified"
                or not isinstance(item.get("sha256"), str)
                or not re.fullmatch("[0-9a-f]{64}", item["sha256"])
                or not isinstance(item.get("shot_pixel_evidence"), list)
                or [x.get("stage") for x in item["shot_pixel_evidence"] if isinstance(x, dict)] != list(STAGES)
                or decoded.get("case_id") != cid or decoded.get("passed") is not True
                or actor.get("case_id") != cid
                or actor.get("character_id") != STORIES[cid][1]
                or actor.get("passed") is not True
                or actor.get("character_identity_semantics") != "not_verified"):
            raise ValueError("Missing independent decode evidence or mismatched preview: " + cid)
        gestures = item.get("decoded_mp4_physical_repair_details")
        expected = PHYSICAL_WITNESSES[cid]
        if (not isinstance(gestures, list) or len(gestures) != len(expected)
                or {g.get("stage") for g in gestures if isinstance(g, dict)} != set(expected)):
            raise ValueError("Missing or unrecognized physical repair evidence: " + cid)
        for g in gestures:
            if (not isinstance(g, dict) or g.get("case_id") != cid
                    or g.get("witness") != expected[g["stage"]][0]
                    or g.get("passed") is not True
                    or g.get("semantics") != "not_verified"
                    or g.get("hand_prop_mechanics") != "not_verified"
                    or g.get("manual_review_required") is not True
                    or not _closed(g)):
                raise ValueError("Incomplete physical action evidence: " + cid)
        video_by_id[cid] = item
    return story_by_id, video_by_id


def decode_frames(path, *, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    """Decode every MP4 frame; report fields cannot replace this verification."""
    if not path.is_file() or path.is_symlink():
        raise ValueError("Absent or unsafe encoded MP4")
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=25,
    )
    streams = json.loads(probe.stdout).get("streams")
    if (not isinstance(streams, list) or len(streams) != 1
            or streams[0].get("codec_type") != "video"
            or streams[0].get("codec_name") != "h264"
            or (streams[0].get("width"), streams[0].get("height")) != SIZE
            or streams[0].get("r_frame_rate") != "12/1"
            or int(streams[0].get("nb_frames", 0)) != FRAMES):
        raise ValueError("Invalid encoded video format, timing or audio stream")
    decoded = subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-i", str(path),
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-an", "pipe:1"],
        check=True, capture_output=True, timeout=60,
    )
    if len(decoded.stdout) != FRAMES * FRAME_BYTES:
        raise ValueError("Decoded MP4 frame count is incomplete or excessive")
    return [Image.frombytes("RGB", SIZE, decoded.stdout[i*FRAME_BYTES:(i+1)*FRAME_BYTES])
            for i in range(FRAMES)]


def _count(image, region, rgb, tol):
    return sum(1 for pixel in image.crop(region).getdata()
               if all(abs(pixel[k] - rgb[k]) <= tol for k in range(3)))


def audit_decoded_frames(cid, frames):
    if cid not in STORIES or not isinstance(frames, list) or len(frames) != FRAMES:
        raise ValueError("Unsupported case or incomplete encoded frame set")
    if any(not isinstance(frame, Image.Image) or frame.size != SIZE or frame.mode != "RGB"
           for frame in frames):
        raise ValueError("Decoded frame dimensions or color space invalid")
    per_beat = {}
    for stage_index, stage in enumerate(STAGES):
        a = frames[stage_index * FRAMES_PER_STAGE].crop(ROI)
        b = frames[(stage_index+1) * FRAMES_PER_STAGE-1].crop(ROI)
        delta = ImageChops.difference(a, b)
        changed = sum(1 for pix in delta.getdata() if max(pix) >= 16)
        per_beat[stage] = {"changed_scene_pixels": changed, "passed": changed >= 64}
    first, last = frames[0], frames[-1]
    cues = {}
    for name, (region, rgb, tol, maximum, minimum) in WITNESSES[cid].items():
        start, end = _count(first, region, rgb, tol), _count(last, region, rgb, tol)
        cues[name] = {"initial_pixels": start, "final_pixels": end,
                      "passed": start <= maximum and end >= minimum}
    gestures = {}
    for stage, (label, region, rgb, tolerance, minimum) in PHYSICAL_WITNESSES[cid].items():
        index = STAGES.index(stage)
        start_frame = frames[index * FRAMES_PER_STAGE]
        end_frame = frames[(index+1)*FRAMES_PER_STAGE-1]
        before = _count(start_frame, region, rgb, tolerance)
        after = _count(end_frame, region, rgb, tolerance)
        gestures[stage] = {
            "gesture": label,
            "early_material_pixels": before,
            "late_material_pixels": after,
            "passed": after >= minimum and after > before + 5,
        }
    if not all(x["passed"] for x in gestures.values()):
        raise ValueError("Encoded MP4 lacks independent physical-action witnesses: " + cid)
    if not all(x["passed"] for x in per_beat.values()) or not all(x["passed"] for x in cues.values()):
        raise ValueError("Encoded MP4 fails source-matched visual-action or payoff witnesses: " + cid)
    return {"four_beat_scene_motion": per_beat, "fixed_profile_payoff_pixels": cues,
            "fixed_profile_physical_actions": gestures,
            "narrative_semantics": "not_verified",
            "character_identity_semantics": "not_verified",
            "manual_visual_and_editorial_review_required": True,
            "approved": False, "production_ready": False, "published": False}


def verify(storyboard_path, previews_dir, source_sha, *, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    if source_sha != SOURCE_SHA:
        raise ValueError("Source SHA differs from pinned #951 artwork and storyboard")
    root = Path(previews_dir)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Missing preview artifact directory")
    storyboard = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    preview_report = json.loads((root / "review-report.json").read_text(encoding="utf-8"))
    stories, previews = validate_metadata(storyboard, preview_report)
    if {p.name for p in root.glob("*.mp4")} != {cid+".mp4" for cid in STORIES}:
        raise ValueError("Unexpected or absent MP4 preview")
    evidence = {}
    for cid in sorted(STORIES):
        file = root / (cid + ".mp4")
        if file.is_symlink() or file.stat().st_size != previews[cid].get("bytes"):
            raise ValueError("Unsafe or modified video size: " + cid)
        actual_sha = hashlib.sha256(file.read_bytes()).hexdigest()
        if actual_sha != previews[cid]["sha256"]:
            raise ValueError("MP4 SHA256 does not match source report: " + cid)
        decoded = decode_frames(file, ffmpeg=ffmpeg, ffprobe=ffprobe)
        evidence[cid] = {
            "story_digest": stories[cid]["story_digest"],
            "character_id": STORIES[cid][1],
            "video_sha256": actual_sha,
            **audit_decoded_frames(cid, decoded),
        }
    return {
        "kind": "astra_offline_story_video_source_bound_v1",
        "source_pr": SOURCE_PR, "source_sha": SOURCE_SHA,
        "case_ids": sorted(STORIES), "story_video_identity_contract_passed": True,
        "decoded_video_motion_and_payoff_pixels_passed": True,
        "decoded_video_authored_physical_action_pixels_passed": True,
        "video_evidence": evidence,
        "source_type": "assistant_authored_reference_not_ai_generated_story",
        "cross_model_story_to_animation_alignment": "not_verified",
        "narrative_semantics": "not_verified",
        "character_visual_identity": "not_verified",
        "cinematic_quality": "not_verified",
        "authenticated_source_provenance": False,
        "manual_editorial_and_visual_review_required": True,
        "production_routing_enabled": False, "paid_apis_used": False,
        "approved": False, "production_ready": False, "published": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--preview-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.storyboard, args.preview_dir, args.source_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ASTRA_OFFLINE_STORY_VIDEO_HANDOFF=" + json.dumps({
        "verified_cases": len(result["case_ids"]),
        "review_only": True, "production_ready": False, "published": False,
    }))


if __name__ == "__main__":
    main()
