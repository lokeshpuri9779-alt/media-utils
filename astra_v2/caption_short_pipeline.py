"""Offline ASTRA pipeline: review-only story JSON -> narration + captions MP4.

This is a local operator-invoked workflow. It does not call Gemini, upload, or publish.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def narration_from_candidate(candidate: dict) -> str:
    """Extract spoken lines from a validated seven-scene candidate in order."""
    if not isinstance(candidate, dict):
        raise ValueError("Candidate must be a JSON object")
    if candidate.get("approved") is True or candidate.get("production_ready") is True:
        raise ValueError("This pipeline accepts review-only candidates, not approval packets")
    if candidate.get("published") is True:
        raise ValueError("Published candidates cannot be reprocessed by this review pipeline")
    scenes = candidate.get("performance_scenes")
    if not isinstance(scenes, list) or len(scenes) != 7:
        raise ValueError("Expected exactly seven performance scenes")
    expected = ["hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff"]
    narration = []
    for index, (scene, role) in enumerate(zip(scenes, expected), start=1):
        if not isinstance(scene, dict) or scene.get("role") != role:
            raise ValueError(f"Scene {index} must have role {role}")
        speech = " ".join(str(scene.get("speech") or "").split())
        if not speech:
            raise ValueError(f"Scene {index} has no narration")
        narration.append(speech)
    return " ".join(narration)


def build(candidate_path: str, output_path: str, voice: str = "af_heart",
          speed: float = 1.04) -> dict:
    source = Path(candidate_path)
    candidate = json.loads(source.read_text(encoding="utf-8"))
    narration = narration_from_candidate(candidate)
    from astra_v2.caption_only_renderer import render_caption_video
    result = render_caption_video(narration, output_path, voice=voice, speed=speed)
    report = {
        "schema_version": 1,
        "candidate_id": candidate.get("content_id") or candidate.get("candidate_id"),
        "title": candidate.get("title"),
        "source": str(source),
        "narration_characters": len(narration),
        "render": result,
        "approved": False,
        "production_ready": False,
        "published": False,
        "next_action": "human_review",
    }
    report_path = Path(output_path).with_suffix(".review.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, help="Review-only candidate JSON")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=1.04)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.candidate, args.output, args.voice, args.speed),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
