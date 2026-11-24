"""Fail-closed aggregation for ASTRA caption-only batch artifacts.

Only candidates with a verified narration/caption MP4 review package enter shared
originality history. Generation alone is not a successful deliverable.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from astra_v2.github_local_story_generator import (
    LANES,
    SOURCED_FACTUAL_LANES,
    accepted_unique_candidates,
    validate_candidate,
    validate_source_pack,
)

REQUIRED_FALSE_FLAGS = ("approved", "production_ready", "published")
MIN_VIDEO_BYTES = 1024


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def validate_rendered_package(candidate_path: Path) -> tuple[dict, dict]:
    """Return candidate and render metadata only when the full package is sound."""
    candidate = _read_json(candidate_path)
    for flag in REQUIRED_FALSE_FLAGS:
        if candidate.get(flag) is not False:
            raise ValueError(f"candidate safety flag {flag} must be false")
    if not candidate.get("premise") or not candidate.get("premise_fingerprint"):
        raise ValueError("candidate premise and fingerprint are required")

    lane = str(candidate.get("content_type") or "")
    if lane not in LANES:
        raise ValueError("candidate content_type is missing or unsupported")
    validated = validate_candidate(candidate, history=[], lane=lane)
    if candidate.get("premise_fingerprint") != validated["premise_fingerprint"]:
        raise ValueError("candidate premise fingerprint does not match its premise")
    if candidate.get("word_count") != validated["word_count"]:
        raise ValueError("candidate word_count does not match its validated narration")
    if candidate.get("content_id") != "rayvan-" + validated["premise_fingerprint"][:20]:
        raise ValueError("candidate content ID does not match its premise fingerprint")
    if lane in SOURCED_FACTUAL_LANES:
        sources = candidate.get("research_sources")
        if not isinstance(sources, list):
            raise ValueError("factual candidate is missing its research source pack")
        validate_source_pack(sources, lane)

    video_path = candidate_path.with_name("rayvan-short.mp4")
    review_path = candidate_path.with_name("rayvan-short.review.json")
    captions_path = candidate_path.with_name("rayvan-short.captions.json")
    if not video_path.is_file() or video_path.stat().st_size < MIN_VIDEO_BYTES:
        raise ValueError("rendered MP4 is missing or too small")
    review = _read_json(review_path)
    captions = _read_json(captions_path)

    for flag in REQUIRED_FALSE_FLAGS:
        if review.get(flag) is not False:
            raise ValueError(f"render review safety flag {flag} must be false")
    render = review.get("render")
    if not isinstance(render, dict) or render.get("quality_check") != "passed":
        raise ValueError("render review does not record a passed quality check")
    if render.get("published") is not False:
        raise ValueError("render review must explicitly confirm unpublished status")
    if Path(str(render.get("output") or "")).name != video_path.name:
        raise ValueError("render review points to a different output file")
    if review.get("candidate_id") != candidate.get("content_id"):
        raise ValueError("render review candidate ID does not match candidate")

    duration = captions.get("duration_seconds")
    render_duration = render.get("duration_seconds")
    caption_rows = captions.get("captions")
    if captions.get("fps") != 30 or not isinstance(caption_rows, list) or not caption_rows:
        raise ValueError("caption sidecar is missing valid 30fps caption timings")
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(float(duration)) or not 28 <= duration <= 40):
        raise ValueError("caption sidecar duration must be between 28 and 40 seconds")
    if (isinstance(render_duration, bool) or not isinstance(render_duration, (int, float))
            or not math.isfinite(float(render_duration))):
        raise ValueError("render review is missing a valid duration")
    if abs(float(duration) - float(render_duration)) > 0.25:
        raise ValueError("caption and render durations do not match")
    previous_end = 0.0
    for index, row in enumerate(caption_rows, 1):
        if not isinstance(row, dict) or not str(row.get("caption") or "").strip():
            raise ValueError(f"caption {index} is missing its text")
        start, end = row.get("start"), row.get("end")
        if (isinstance(start, bool) or isinstance(end, bool)
                or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                or not math.isfinite(float(start)) or not math.isfinite(float(end))
                or start < previous_end or end <= start or end > float(duration) + 0.1):
            raise ValueError(f"caption {index} has invalid or out-of-order timing")
        previous_end = float(end)
    return candidate, {
        "video": str(video_path),
        "review": str(review_path),
        "captions": str(captions_path),
        "duration_seconds": round(float(duration), 3),
    }


def aggregate_batch(history_path: str | Path, batch_dir: str | Path,
                    run_id: str | int, batch_result: str) -> dict:
    history_path = Path(history_path)
    batch_dir = Path(batch_dir)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    batch_dir.mkdir(parents=True, exist_ok=True)

    history_rows = []
    if history_path.exists():
        for line_number, line in enumerate(history_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Corrupt history JSON on line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Originality history line {line_number} must be a JSON object")
            if row.get("premise"):
                history_rows.append(row)

    candidate_paths = sorted(batch_dir.glob("**/candidate.json"))
    verified = []
    rejected = []
    package_checks = []
    for path in candidate_paths:
        try:
            candidate, package = validate_rendered_package(path)
            verified.append(candidate)
            package_checks.append(package)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            rejected.append({"candidate": str(path), "reason": str(exc)})

    accepted, duplicates = accepted_unique_candidates(verified, history_rows)
    added = [
        {
            "title": candidate.get("title", ""),
            "premise": candidate["premise"],
            "fingerprint": candidate["premise_fingerprint"],
        }
        for candidate in accepted
    ]
    if added:
        with history_path.open("a", encoding="utf-8") as handle:
            for row in added:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "run_id": str(run_id),
        "batch_result": batch_result,
        "candidate_files_found": len(candidate_paths),
        "rendered_packages_verified": len(verified),
        "rejected_packages": rejected,
        "accepted_unique_candidates": len(accepted),
        "duplicate_candidates": duplicates,
        "new_history_records": len(added),
        "verified_packages": package_checks,
        "review_only": True,
        "published": False,
    }
    (batch_dir / "batch-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", required=True)
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch-result", required=True)
    args = parser.parse_args(argv)
    report = aggregate_batch(args.history, args.batch_dir, args.run_id, args.batch_result)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
