"""Fail-closed, review-only proof packet for isolated ASTRA CPU story experiments.

This binds the *files* and independent validation reports from one run in an
auditable SHA256 manifest. It is NOT an approval, provenance certification,
semantic quality score, renderer router, or publishing path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from tools.experimental_video_frame_consistency import compare_video

PROFILES = {
    "frog": {
        "story_id": "astra-frog-seed-rescue",
        "frame_count": 32,
        "fps": 6,
        "video": "frog_story_previs.mp4",
        "audit": "visual_motion_audit.json",
        "audit_pass": "passed",
        "negative": "visual_motion_negative_controls.json",
        "negative_count": 7,
        "object_audit": "object_pixel_tracks.json",
        "object_negative": "object_pixel_negative_controls.json",
        "object_negative_count": 10,
    },
    "lighthouse": {
        "story_id": "astra-coastal-spark",
        "frame_count": 20,
        "fps": 8,
        "video": "story_previs.mp4",
        "audit": "visual_audit.json",
        "audit_pass": "passes_fixed_pixel_checks",
        "negative": "negative_controls.json",
        "negative_count": 5,
    },
}
REQUIRED_SAFETY = ("approved", "published", "production_ready", "paid_apis_used")
DIMENSIONS = (384, 576)
FPS = "8/1"


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def read_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return data


def png_dimensions(path):
    with path.open("rb") as f:
        h = f.read(24)
    if len(h) != 24 or not h.startswith(b"\x89PNG\r\n\x1a\n") or h[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG header in {path.name}")
    return struct.unpack(">II", h[16:24])


def get_video(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames",
         "-of", "json", str(path)],
        text=True, capture_output=True, check=True,
    )
    streams = json.loads(result.stdout)["streams"]
    if len(streams) != 1:
        raise ValueError("Expected one video stream")
    return streams[0]


def closed(doc):
    return all(doc.get(x) is False for x in REQUIRED_SAFETY)


def all_checks(doc):
    checks = doc.get("checks")
    return isinstance(checks, dict) and bool(checks) and all(
        value is True for value in checks.values()
    )


def build(directory, profile):
    if profile not in PROFILES:
        raise ValueError(f"Unsupported review profile: {profile}")
    cfg = PROFILES[profile]
    directory = Path(directory)
    checks = {}
    hashes = {}
    reports = {}
    expected = {
        "review": "review.json",
        "action": "action_contract.json",
        "visual": cfg["audit"],
        "negative": cfg["negative"],
    }
    if profile == "frog":
        expected.update({
            "object_pixel": cfg["object_audit"],
            "object_negative": cfg["object_negative"],
        })
    for key, name in expected.items():
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name}: fail closed")
        reports[key] = read_json(path)
        hashes[name] = digest(path)

    review, action, visual, negative = (
        reports[k] for k in ("review", "action", "visual", "negative")
    )
    checks["correct_story_profile"] = (
        (profile == "lighthouse" and review.get("plot_fingerprint") is not None)
        or review.get("story_id") == cfg["story_id"]
    )
    checks["all_source_gates_closed"] = all(closed(p) for p in reports.values())
    checks["manual_review_retained"] = (
        review.get("editorial_review_required") is True
        and action.get("manual_review_required") is True
        and (visual.get("manual_visual_review_required") is True
             if profile == "frog"
             else visual.get("manual_editorial_review_required") is True)
        and (negative.get("manual_visual_review_required") is True
             if profile == "frog"
             else negative.get("manual_review_required") is True)
    )
    checks["original_render_structural_checks"] = (
        review.get("success") is True and all_checks(review)
    )
    checks["shared_action_contract"] = (
        action.get("profile") == profile
        and action.get("passed") is True
        and all_checks(action)
    )
    checks["visual_pixel_audit"] = (
        visual.get(cfg["audit_pass"]) is True
        and all_checks(visual)
        and (visual.get("profile") == profile if profile == "frog" else True)
    )
    checks["negative_controls_rejected"] = (
        negative.get("all_corruptions_rejected") is True
        and negative.get("negative_case_count") == cfg["negative_count"]
    )
    checks["no_claim_of_semantic_quality"] = (
        action.get("semantic_quality") == "not_verified"
        and (visual.get("semantic_quality") if profile == "frog"
             else visual.get("visual_semantic_quality")) == "not_verified"
    )
    if profile == "frog":
        object_pixel = reports["object_pixel"]
        object_negative = reports["object_negative"]
        required_cues = (
            "review_only_fixed_camera_trace",
            "magnet_golden_pixels_present",
            "gold_cluster_travels_leftward_to_clip",
            "airplane_bright_pixels_present",
            "paper_region_moves_right_after_contact",
            "seed_brown_blob_before_soil",
            "seed_pixel_path_advances_toward_pot",
            "seed_visibly_contrasts_with_pot_soil",
            "sprout_pixels_follow_seed_transfer",
        )
        checks["frog_object_pixel_tracking"] = (
            object_pixel.get("passed") is True
            and all_checks(object_pixel)
            and all(object_pixel["checks"].get(cue) is True for cue in required_cues)
            and object_pixel.get("manual_visual_review_required") is True
            and object_pixel.get("semantic_quality") == "not_verified"
        )
        cases = object_negative.get("cases")
        checks["frog_object_negative_controls"] = (
            object_negative.get("source_passed") is True
            and object_negative.get("all_corruptions_rejected") is True
            and object_negative.get("negative_case_count")
                == cfg["object_negative_count"]
            and isinstance(cases, list)
            and len(cases) == cfg["object_negative_count"]
            and all(isinstance(case, dict) and case.get("rejected") is True
                    for case in cases)
            and object_negative.get("manual_visual_review_required") is True
            and object_negative.get("semantic_quality") == "not_verified"
        )
        checks["no_claim_of_semantic_quality"] = (
            checks["no_claim_of_semantic_quality"]
            and object_pixel.get("semantic_quality") == "not_verified"
            and object_negative.get("semantic_quality") == "not_verified"
        )
    frames = review.get("frames")
    expected_count = cfg["frame_count"]
    checks["frame_metadata_complete"] = (
        isinstance(frames, list)
        and len(frames) == expected_count
        and all(isinstance(f, dict) and f.get("frame") == i
                for i, f in enumerate(frames))
    )
    frame_files = sorted(directory.glob("frame_*.png"))
    checks["exact_frame_files"] = len(frame_files) == expected_count and all(
        (directory / f"frame_{i:03d}.png").is_file()
        for i in range(expected_count)
    )
    checks["png_headers_and_resolution"] = checks["exact_frame_files"] and all(
        png_dimensions(directory / f"frame_{i:03d}.png") == DIMENSIONS
        for i in range(expected_count)
    )
    checks["lighthouse_existing_frame_hashes_match"] = True
    if checks["exact_frame_files"]:
        for i in range(expected_count):
            name = f"frame_{i:03d}.png"
            path = directory / name
            hashes[name] = digest(path)
            if profile == "lighthouse" and checks["frame_metadata_complete"]:
                if frames[i].get("sha256") != hashes[name]:
                    checks["lighthouse_existing_frame_hashes_match"] = False
    if profile == "lighthouse":
        plan_path = directory / "shot_plan.json"
        if not plan_path.is_file():
            raise FileNotFoundError("Missing lighthouse storyboard")
        shot_plan = read_json(plan_path)
        hashes[plan_path.name] = digest(plan_path)
        checks["storyboard_bound_to_render"] = (
            shot_plan.get("story_id") == cfg["story_id"]
            and shot_plan.get("plot_fingerprint") == review.get("plot_fingerprint")
            and closed(shot_plan)
        )
    video_path = directory / cfg["video"]
    if not video_path.is_file():
        raise FileNotFoundError(f"Missing encoded video {cfg['video']}")
    video = get_video(video_path)
    hashes[video_path.name] = digest(video_path)
    checks["video_matches_story_frames"] = (
        video.get("codec_name") == "h264"
        and (video.get("width"), video.get("height")) == DIMENSIONS
        and video.get("r_frame_rate") == f"{cfg['fps']}/1"
        and int(video.get("nb_frames", -1)) == expected_count
        and video_path.stat().st_size > 4096
    )

    # Prior manifests authenticated the *files* only. Independently decode the
    # H.264 video and PNG sequence: a valid-but-unrelated MP4 must fail review.
    video_frame_content = None
    if checks["exact_frame_files"] and checks["video_matches_story_frames"]:
        try:
            video_frame_content = compare_video(
                directory, cfg["video"], expected_count
            )
        except (OSError, ValueError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            pass
    checks["encoded_video_pixels_match_png_sequence"] = (
        video_frame_content is not None
        and video_frame_content.get("passed") is True
    )

    failed = sorted(k for k, v in checks.items() if not v)
    return {
        "kind": "isolated_unapproved_story_review_manifest",
        "profile": profile,
        "story_id": cfg["story_id"],
        "technical_evidence_passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "frame_count": expected_count,
        "fps": cfg["fps"],
        "frame_dimensions": list(DIMENSIONS),
        "video": cfg["video"],
        "video_frame_content_evidence": video_frame_content,
        "sha256": hashes,
        "approval": "manual_review_required",
        "semantic_quality": "not_verified",
        "cinematic_quality": "not_verified",
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "warning": "SHA256 ties files in this packet together; does not prove artistic quality or tamper resistance.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    args = parser.parse_args()
    result = build(args.directory, args.profile)
    output = args.directory / "story_review_manifest.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("ASTRA_REVIEW_MANIFEST=" + json.dumps({
        "profile": result["profile"],
        "passed": result["technical_evidence_passed"],
        "failed": result["failed_checks"],
        "files": len(result["sha256"]),
        "production_ready": False,
    }), flush=True)
    if not result["technical_evidence_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
