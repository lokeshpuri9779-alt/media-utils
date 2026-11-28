"""Stage one exact owner-authorized review-only story; never approve or publish it."""
import argparse
import json
from pathlib import Path

from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.gemini_art_staging import generate_staged_art
from astra_v2.gemini_art_semantic_review import review


def load_candidate(path, expected_content_id, expected_digest):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if (doc.get("schema") != "astra.art.review-only-candidate.v1"
            or doc.get("status") != "pending_review"
            or doc.get("publication_triggered") is not False):
        raise ValueError("invalid_review_only_candidate_envelope")
    story = doc.get("story")
    if not isinstance(story, dict):
        raise ValueError("review_only_story_missing")
    if story.get("content_id") != expected_content_id:
        raise ValueError("review_only_content_id_mismatch")
    digest = story_digest(story)
    if digest != expected_digest or doc.get("story_sha256") != digest:
        raise ValueError("review_only_story_digest_mismatch")
    if story.get("production_ready") is not False:
        raise ValueError("review_only_story_must_not_be_production_ready")
    beats = story.get("story_beats")
    if not isinstance(beats, list) or len(beats) != 4:
        raise ValueError("unexpected_review_only_scene_count")
    return story


def stage_review_only(candidate_path, content_id, expected_digest, destination):
    story = load_candidate(candidate_path, content_id, expected_digest)
    manifest = generate_staged_art(story, destination)
    technical_path = Path(destination) / "technical-review.json"
    from astra_v2.staged_art_technical_review import audit_staged_art
    technical = audit_staged_art(manifest)
    technical_path.write_text(json.dumps(technical, indent=2) + "\\n", encoding="utf-8")
    if not technical["technical_pass"]:
        raise ValueError("review_only_technical_qa_failed")
    semantic = review(story, manifest)
    semantic_path = Path(destination) / "semantic-review.json"
    semantic_path.write_text(json.dumps(semantic, indent=2) + "\\n", encoding="utf-8")
    report = {
        "schema": "astra.art.review-only-report.v1",
        "content_id": content_id,
        "story_sha256": expected_digest,
        "staged_asset_count": len(json.loads(manifest.read_text())["assets"]),
        "technical_pass": technical["technical_pass"],
        "semantic_pass": semantic["semantic_pass"],
        "independent_visual_approval": False,
        "production_approved": False,
        "publication_triggered": False,
        "status": "pending_human_review"
    }
    (Path(destination) / "review-only-report.json").write_text(
        json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--story-sha256", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(json.dumps(stage_review_only(args.candidate, args.content_id,
                                       args.story_sha256, args.destination), sort_keys=True))
