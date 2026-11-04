"""Source-pinned, review-only ASTRA cross-experiment integration contract.

The actual story and motion regressions run independently in the same CI run.
This file combines their *test completion* receipts, not their media or models.
Even a passing receipt cannot authorize output, semantic quality or publishing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

KIND = "astra_offline_crosspr_lane_v1"
EXPECTED = {
    "story": {
        "pr": 951,
        "sha": "b1fb13e98865f0ab177c2df0aa98707f0ac2954a",
        "tests": [
            "tests.test_astra_offline_llm",
            "tests.test_astra_offline_blind_review",
            "tests.test_astra_offline_storyboard",
        ],
    },
    "motion": {
        "pr": 929,
        "sha": "cc18200b99f6e5d57c8377146de38eae392810c8",
        "tests": [
            "tests.test_astra_experimental_action_contracts",
            "tests.test_astra_experimental_story_review_verify",
            "tests.test_astra_experimental_video_frame_consistency",
        ],
    },
    "video": {
        "pr": 951,
        "sha": "b1fb13e98865f0ab177c2df0aa98707f0ac2954a",
        "tests": [
            "tests.test_astra_offline_story_video_handoff",
            "tests.test_astra_offline_procedural_preview",
            "tests.test_astra_offline_visual_cues",
            "tests.test_astra_offline_character_rig",
        ],
    },
}
CLOSED = ("approved", "published", "production_ready", "paid_apis_used",
          "production_routing_enabled", "real_model_inference_executed",
          "new_render_executed")


def digest(document):
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def lane_report(lane, source_sha, evidence_sha=None):
    """Build a receipt *after* the matrix step ran each pinned suite successfully."""
    if lane not in EXPECTED:
        raise ValueError("Unknown offline research lane")
    spec = EXPECTED[lane]
    if source_sha != spec["sha"] or not re.fullmatch("[0-9a-f]{40}", source_sha):
        raise ValueError("Experiment checkout differs from pinned audited commit")
    report = {
        "kind": KIND,
        "lane": lane,
        "source_pr": spec["pr"],
        "source_sha": source_sha,
        "unit_test_modules": list(spec["tests"]),
        "tests_completed": True,
        "manual_editorial_review_required": True,
        "manual_visual_review_required": True,
        "semantic_quality": "not_verified",
        "story_motion_alignment": "not_verified",
        "cinematic_quality": "not_verified",
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "production_routing_enabled": False,
        "real_model_inference_executed": False,
        "new_render_executed": False,
    }
    if lane == "video":
        if not isinstance(evidence_sha, str) or not re.fullmatch("[0-9a-f]{64}", evidence_sha):
            raise ValueError("Video review requires a real decoded-MP4 evidence hash")
        report["source_matched_encoded_video_evidence_sha256"] = evidence_sha
    elif evidence_sha is not None:
        raise ValueError("Only video review may supply a decoded artifact hash")
    report["report_sha256"] = digest(report)
    return report


def validate_lane(value, lane, evidence_sha=None):
    if lane not in EXPECTED or not isinstance(value, dict):
        raise ValueError("Unknown or malformed cross-PR review lane")
    expected = lane_report(lane, EXPECTED[lane]["sha"], evidence_sha=evidence_sha)
    if value != expected:
        raise ValueError("Missing, stale, modified or unsafe offline review receipt")
    if any(value.get(key) is not False for key in CLOSED):
        raise ValueError("A review receipt must never enable production")
    return True


def aggregate(directory):
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Missing or unsafe cross-PR review directory")
    files = sorted(root.iterdir())
    if (any(path.is_symlink() or not path.is_file() for path in files)
            or {p.name for p in files} != {"story.json", "motion.json", "video.json", "video-evidence.json"}):
        raise ValueError("All three pinned review receipts and decoded video evidence are required")
    evidence_path = root / "video-evidence.json"
    if evidence_path.stat().st_size > 100_000:
        raise ValueError("Unbounded decoded-video evidence")
    evidence_bytes = evidence_path.read_bytes()
    try:
        video_evidence = json.loads(evidence_bytes)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Unparseable decoded-video proof") from exc
    if (not isinstance(video_evidence, dict)
            or video_evidence.get("source_pr") != 951
            or video_evidence.get("source_sha") != EXPECTED["video"]["sha"]
            or video_evidence.get("case_ids") != [
                "footbridge-ducklings", "glasshouse-sunshade", "moon-mirror-garden"
            ]
            or video_evidence.get("story_video_identity_contract_passed") is not True
            or video_evidence.get("decoded_video_motion_and_payoff_pixels_passed") is not True
            or video_evidence.get("source_type") != "assistant_authored_reference_not_ai_generated_story"
            or video_evidence.get("cross_model_story_to_animation_alignment") != "not_verified"
            or video_evidence.get("manual_editorial_and_visual_review_required") is not True
            or video_evidence.get("authenticated_source_provenance") is not False
            or any(video_evidence.get(k) is not False for k in
                   ("approved", "production_ready", "published", "production_routing_enabled", "paid_apis_used"))):
        raise ValueError("Unsafe, mismatched or incomplete decoded video evidence")
    proof = video_evidence.get("video_evidence")
    if (not isinstance(proof, dict) or set(proof) != set(video_evidence["case_ids"])
            or any(not isinstance(item, dict)
                   or item.get("narrative_semantics") != "not_verified"
                   or len(item.get("four_beat_scene_motion", {})) != 4
                   or not all(v.get("passed") is True
                              for v in item["four_beat_scene_motion"].values())
                   or len(item.get("fixed_profile_payoff_pixels", {})) != 2
                   or not all(v.get("passed") is True
                              for v in item["fixed_profile_payoff_pixels"].values())
                   for item in proof.values())):
        raise ValueError("Incomplete per-story encoded action/payoff evidence")
    evidence_sha = hashlib.sha256(evidence_bytes).hexdigest()
    hashes = {}
    for lane in sorted(EXPECTED):
        path = root / (lane + ".json")
        if path.stat().st_size > 16_384:
            raise ValueError("Review-lane receipt is unexpectedly large")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise ValueError("Unparseable cross-PR receipt") from exc
        validate_lane(value, lane, evidence_sha=evidence_sha if lane == "video" else None)
        hashes[lane] = value["report_sha256"]
    return {
        "kind": "astra_offline_crosspr_aggregate_v1",
        "review_only_technical_contract_passed": True,
        "lanes": sorted(EXPECTED),
        "source_prs": {k: EXPECTED[k]["pr"] for k in sorted(EXPECTED)},
        "source_shas": {k: EXPECTED[k]["sha"] for k in sorted(EXPECTED)},
        "receipt_sha256": hashes,
        "decoded_story_video_evidence_sha256": evidence_sha,
        "authored_reference_video_payoff_pixel_checks": True,
        "actual_model_story_quality": "not_verified",
        "motion_semantic_fidelity": "not_verified",
        "cross_story_motion_alignment": "not_verified",
        "manual_editorial_review_required": True,
        "manual_visual_review_required": True,
        "signed_evidence": False,
        "approved": False,
        "production_ready": False,
        "published": False,
        "paid_apis_used": False,
        "production_routing_enabled": False,
        "warning": "Passing isolated tests is not quality approval; receipts are unsigned and source-pinned.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    lane_cmd = sub.add_parser("lane")
    lane_cmd.add_argument("--lane", required=True, choices=sorted(EXPECTED))
    lane_cmd.add_argument("--source-dir", required=True, type=Path)
    lane_cmd.add_argument("--output", required=True, type=Path)
    lane_cmd.add_argument("--evidence-file", type=Path)
    agg_cmd = sub.add_parser("aggregate")
    agg_cmd.add_argument("--directory", required=True, type=Path)
    agg_cmd.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "lane":
        sha = subprocess.check_output(
            ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"],
            text=True, timeout=15).strip()
        proof_sha = hashlib.sha256(args.evidence_file.read_bytes()).hexdigest() if args.evidence_file else None
        report = lane_report(args.lane, sha, evidence_sha=proof_sha)
    else:
        report = aggregate(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("ASTRA_OFFLINE_CROSSPR_REVIEW=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
