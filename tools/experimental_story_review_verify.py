"""Independently verify SHA256-bound isolated ASTRA review artifacts.

Use AFTER the review manifest is written, including on a downloaded artifact.
The manifest itself is not signed; coordinated modification of files and the
manifest cannot be detected. Never approves assets, publishing, or semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.experimental_story_review_manifest import (
    DIMENSIONS, FPS, PROFILES, closed, get_video, png_dimensions,
)
from tools.experimental_video_frame_consistency import compare_video

HASHLEN = 64
SAFETY = ("approved", "published", "production_ready", "paid_apis_used")


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify(directory, profile):
    if profile not in PROFILES:
        raise ValueError("Unknown isolated story profile")
    root = Path(directory)
    cfg = PROFILES[profile]
    manifest_file = root / "story_review_manifest.json"
    if not manifest_file.is_file() or manifest_file.is_symlink():
        raise ValueError("Missing or unsafe review manifest")
    try:
        doc = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Corrupt review manifest") from exc
    if not isinstance(doc, dict):
        raise ValueError("Review manifest must be a JSON object")

    names = {f"frame_{i:03d}.png" for i in range(cfg["frame_count"])}
    names.update((
        "review.json", "action_contract.json",
        cfg["audit"], cfg["negative"], cfg["video"],
    ))
    if profile == "lighthouse":
        names.add("shot_plan.json")
    else:
        names.update((cfg["object_audit"], cfg["object_negative"]))

    declared = doc.get("sha256")
    checks = {
        "expected_profile_and_story": (
            doc.get("kind") == "isolated_unapproved_story_review_manifest"
            and doc.get("profile") == profile
            and doc.get("story_id") == cfg["story_id"]
            and doc.get("frame_count") == cfg["frame_count"]
            and doc.get("fps") == cfg["fps"]
            and doc.get("frame_dimensions") == list(DIMENSIONS)
            and doc.get("video") == cfg["video"]
        ),
        "prior_technical_checks_present": (
            doc.get("technical_evidence_passed") is True
            and isinstance(doc.get("checks"), dict)
            and bool(doc["checks"])
            and all(v is True for v in doc["checks"].values())
            and doc.get("failed_checks") == []
        ),
        "manual_review_required": (
            doc.get("approval") == "manual_review_required"
            and doc.get("semantic_quality") == "not_verified"
            and doc.get("cinematic_quality") == "not_verified"
            and closed(doc)
        ),
        "complete_hash_inventory": (
            isinstance(declared, dict)
            and set(declared) == names
            and all(isinstance(v, str) and len(v) == HASHLEN
                    and all(ch in "0123456789abcdef" for ch in v)
                    for v in declared.values())
        ),
        "no_unexpected_files": (
            root.is_dir()
            and {p.name for p in root.iterdir() if p.is_file()} <= (
                names | {"story_review_manifest.json", "story_review_verification.json"}
            )
            and not any(p.is_symlink() for p in root.iterdir())
        ),
    }

    mismatches = []
    if checks["complete_hash_inventory"]:
        for name in sorted(names):
            path = root / name
            if not path.is_file() or path.is_symlink() or sha256(path) != declared[name]:
                mismatches.append(name)
    else:
        mismatches = sorted(names)

    checks["every_file_matches_recorded_sha256"] = not mismatches
    try:
        checks["all_png_headers_match_format"] = all(
            png_dimensions(root / f"frame_{i:03d}.png") == DIMENSIONS
            for i in range(cfg["frame_count"])
        )
    except (OSError, ValueError):
        checks["all_png_headers_match_format"] = False

    try:
        video = get_video(root / cfg["video"])
        checks["independently_verified_h264_video"] = (
            video.get("codec_name") == "h264"
            and (video.get("width"), video.get("height")) == DIMENSIONS
            and video.get("r_frame_rate") == f"{cfg['fps']}/1"
            and int(video.get("nb_frames", -1)) == cfg["frame_count"]
        )
    except (OSError, ValueError, KeyError, RuntimeError, IndexError,
            __import__("subprocess").CalledProcessError):
        checks["independently_verified_h264_video"] = False

    # Hashes cannot detect a fabricated, internally self-consistent manifest
    # around a valid-but-unrelated MP4. Compare independently decoded pixels.
    # This test checks content correspondence only, not artistic quality.
    fresh_video_evidence = None
    if checks["complete_hash_inventory"] and checks["every_file_matches_recorded_sha256"]:
        try:
            fresh_video_evidence = compare_video(root, cfg["video"], cfg["frame_count"])
        except (OSError, ValueError, __import__("subprocess").CalledProcessError,
                __import__("subprocess").TimeoutExpired):
            pass
    checks["video_pixels_independently_match_png_sequence"] = (
        fresh_video_evidence is not None
        and fresh_video_evidence.get("passed") is True
    )
    checks["manifest_and_independent_fidelity_evidence_agree"] = (
        fresh_video_evidence is not None
        and doc.get("video_frame_content_evidence") == fresh_video_evidence
    )

    failed = sorted(k for k, v in checks.items() if v is not True)
    return {
        "kind": "isolated_story_review_artifact_verification",
        "profile": profile,
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "mismatched_files": mismatches,
        "files_verified": len(names) - len(mismatches),
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "manual_visual_review_required": True,
        "semantic_quality": "not_verified",
        "warning": (
            "Hashes detect changes relative to this manifest; not authentic "
            "signatures, independent source provenance, or artistic review."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    outcome = verify(args.directory, args.profile)
    (args.directory / "story_review_verification.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("ASTRA_STORY_REVIEW_VERIFICATION=" + json.dumps({
        "profile": args.profile, "passed": outcome["passed"],
        "checks": outcome["checks"], "failed": outcome["failed_checks"],
        "files_verified": outcome["files_verified"],
        "approved": False, "production_ready": False,
    }), flush=True)
    if not outcome["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
