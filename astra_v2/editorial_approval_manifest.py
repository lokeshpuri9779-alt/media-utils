"""Fail-closed editorial decision manifest for authored production candidates.

Review records document an external editorial decision; they never convert
procedural proposals into approved authored stories.
"""
import hashlib
import json
from pathlib import Path
from astra_v2.production_story_gate import candidate_issues


def story_digest(story):
    """Bind review to the exact immutable story payload."""
    payload = json.dumps(story, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def review_decision(story, record, history=()):
    """Return blocking reasons; approval never overrides production checks."""
    issues = candidate_issues(story, history)
    if not isinstance(record, dict):
        return sorted(set(issues + ["missing_editorial_record"]))
    if record.get("content_id") != story.get("content_id"):
        issues.append("review_content_id_mismatch")
    if record.get("story_sha256") != story_digest(story):
        issues.append("review_story_digest_mismatch")
    if record.get("decision") != "approve":
        issues.append("editorial_approval_missing")
    if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        issues.append("reviewer_missing")
    if not isinstance(record.get("review_notes"), str) or not record["review_notes"].strip():
        issues.append("review_notes_missing")
    return sorted(set(issues))


def validate_manifest(stories, records, history=()):
    """Audit all decisions; duplicate IDs and reused approvals fail closed."""
    if not isinstance(stories, list) or not isinstance(records, list):
        raise ValueError("Stories and review records must be lists")
    ids = [s.get("content_id") for s in stories if isinstance(s, dict)]
    if len(ids) != len(stories) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or duplicate story IDs")
    record_ids = [r.get("content_id") for r in records if isinstance(r, dict)]
    if len(record_ids) != len(records) or len(set(record_ids)) != len(record_ids):
        raise ValueError("Invalid or duplicate review record IDs")
    if set(record_ids) - set(ids):
        raise ValueError("Review records reference unknown stories")
    by_id = {r["content_id"]: r for r in records}
    results = []
    seen = list(history)
    for story in stories:
        issues = review_decision(story, by_id.get(story["content_id"]), seen)
        results.append({"content_id": story["content_id"], "approved": not issues,
                        "issues": issues})
        if not issues:
            seen.append(story)
    return {"results": results, "approved_count": sum(x["approved"] for x in results),
            "publication_triggered": False}


def audit_files(stories_path, reviews_path):
    stories = json.loads(Path(stories_path).read_text(encoding="utf-8"))
    reviews = json.loads(Path(reviews_path).read_text(encoding="utf-8"))
    return validate_manifest(stories["stories"], reviews["reviews"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--reviews", required=True)
    args = parser.parse_args()
    print("ASTRA_EDITORIAL_AUDIT=" + json.dumps(
        audit_files(args.stories, args.reviews), sort_keys=True))
