"""Offline ASTRA pipeline: review-only story JSON -> narration + captions MP4.

This is a local operator-invoked workflow. It does not call Gemini, upload, or publish.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def narration_from_candidate(candidate: dict) -> str:
    """Extract spoken lines from any supported lane-specific candidate in order."""
    if not isinstance(candidate, dict):
        raise ValueError("Candidate must be a JSON object")
    if candidate.get("approved") is True or candidate.get("production_ready") is True:
        raise ValueError("This pipeline accepts review-only candidates, not approval packets")
    if candidate.get("published") is True:
        raise ValueError("Published candidates cannot be reprocessed by this review pipeline")
    scenes = candidate.get("performance_scenes")
    if not isinstance(scenes, list) or len(scenes) not in (4, 7):
        raise ValueError("Expected four compact-format scenes or seven story beats")
    narration = []
    seen_roles = set()
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict) or not str(scene.get("role") or "").strip():
            raise ValueError(f"Scene {index} must include a role")
        role = str(scene["role"]).strip()
        if role in seen_roles:
            raise ValueError(f"Scene {index} repeats role {role}")
        seen_roles.add(role)
        speech = " ".join(str(scene.get("speech") or "").split())
        if not speech:
            raise ValueError(f"Scene {index} has no narration")
        narration.append(speech)
    engagement_question = " ".join(str(candidate.get("question") or "").split())
    if not engagement_question:
        raise ValueError("Candidate must include an audience engagement question")
    if engagement_question.rstrip()[-1:] not in ".!?":
        engagement_question += "?"
    narration.append(engagement_question)
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
