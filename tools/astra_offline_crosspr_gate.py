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
        "sha": "63f98ea1e62eece7847311c0fe6d59165ba6a863",
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
}
CLOSED = ("approved", "published", "production_ready", "paid_apis_used",
          "production_routing_enabled", "real_model_inference_executed",
          "new_render_executed")


def digest(document):
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def lane_report(lane, source_sha):
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
    report["report_sha256"] = digest(report)
    return report


def validate_lane(value, lane):
    if lane not in EXPECTED or not isinstance(value, dict):
        raise ValueError("Unknown or malformed cross-PR review lane")
    expected = lane_report(lane, EXPECTED[lane]["sha"])
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
            or {p.name for p in files} != {"story.json", "motion.json"}):
        raise ValueError("Both and only both review-lane receipts are required")
    hashes = {}
    for lane in sorted(EXPECTED):
        path = root / (lane + ".json")
        if path.stat().st_size > 16_384:
            raise ValueError("Review-lane receipt is unexpectedly large")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise ValueError("Unparseable cross-PR receipt") from exc
        validate_lane(value, lane)
        hashes[lane] = value["report_sha256"]
    return {
        "kind": "astra_offline_crosspr_aggregate_v1",
        "review_only_technical_contract_passed": True,
        "lanes": sorted(EXPECTED),
        "source_prs": {k: EXPECTED[k]["pr"] for k in sorted(EXPECTED)},
        "source_shas": {k: EXPECTED[k]["sha"] for k in sorted(EXPECTED)},
        "receipt_sha256": hashes,
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
    agg_cmd = sub.add_parser("aggregate")
    agg_cmd.add_argument("--directory", required=True, type=Path)
    agg_cmd.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "lane":
        sha = subprocess.check_output(
            ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"],
            text=True, timeout=15).strip()
        report = lane_report(args.lane, sha)
    else:
        report = aggregate(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("ASTRA_OFFLINE_CROSSPR_REVIEW=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
