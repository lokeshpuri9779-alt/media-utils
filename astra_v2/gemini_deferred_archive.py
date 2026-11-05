"""Persist a bounded, unapproved Gemini-deferred review archive.

This file is not an inventory or intake. No renderer, editorial verdict,
provider request, production fallback or publisher reads it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

MAX_BATCH = 50
MAX_ENTRIES = 100
MAX_PROPOSAL_BYTES = 120_000
MAX_OUTPUT_BYTES = 4_000_000
ARCHIVE_STATUS = "deferred_review_only"


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def build_archive(proposals, audit, previous=None, run_id=""):
    """Keep only explicitly deferred proposals; never grant any approval."""
    stories = proposals.get("stories") if isinstance(proposals, dict) else None
    reviews = audit.get("reviews") if isinstance(audit, dict) else None
    if (not isinstance(proposals, dict) or proposals.get("status") != "unreviewed"
            or not isinstance(stories, list) or len(stories) > MAX_BATCH
            or not isinstance(reviews, list) or len(reviews) != len(stories)):
        raise ValueError("invalid_deferred_review_source")
    if previous is None:
        entries = []
    else:
        if (not isinstance(previous, dict) or previous.get("version") != 1
                or previous.get("status") != ARCHIVE_STATUS
                or previous.get("publication_approval") is not False
                or previous.get("eligible_for_automatic_publishing") is not False
                or not isinstance(previous.get("entries"), list)
                or len(previous["entries"]) > MAX_ENTRIES):
            raise ValueError("invalid_deferred_review_archive")
        entries = list(previous["entries"])
        for entry in entries:
            if (not isinstance(entry, dict)
                    or entry.get("review_status") != "deferred_unreviewed"
                    or not isinstance(entry.get("source_sha256"), str)
                    or not isinstance(entry.get("proposal"), dict)):
                raise ValueError("invalid_deferred_review_entry")

    known = {row["source_sha256"] for row in entries}
    added = 0
    for story, review in zip(stories, reviews):
        if (not isinstance(story, dict) or not isinstance(review, dict)
                or not isinstance(story.get("content_id"), str)
                or not story["content_id"]
                or review.get("content_id") != story["content_id"]):
            raise ValueError("deferred_review_identity_mismatch")
        issues = review.get("issues")
        if not isinstance(issues, list) or any(not isinstance(i, str) for i in issues):
            raise ValueError("invalid_deferred_review_issues")
        # Approved and genuine rejected candidates are deliberately not archived.
        if review.get("approved") is not False:
            continue
        reasons = [i for i in issues if i in (
            "review_deferred:rate_limited", "review_deferred:provider_unavailable",
            "review_deferred:timeout", "review_deferred:transport_unavailable")]
        if not reasons:
            continue
        payload = _encoded(story)
        if len(payload) > MAX_PROPOSAL_BYTES:
            raise ValueError("deferred_proposal_too_large")
        digest = hashlib.sha256(payload).hexdigest()
        if digest in known:
            continue
        entries.append({
            "source_sha256": digest,
            "content_id": story["content_id"],
            "review_status": "deferred_unreviewed",
            "deferred_reason": reasons[0],
            "source_run_id": str(run_id)[:32] if str(run_id).isdigit() else "",
            "proposal": story,
        })
        known.add(digest)
        added += 1
    entries = entries[-MAX_ENTRIES:]
    output = {
        "version": 1, "status": ARCHIVE_STATUS,
        "publication_approval": False,
        "eligible_for_automatic_publishing": False,
        "entries": entries,
    }
    # Bound storage in the private state branch; oldest deferred rows go first.
    while entries and len(_encoded(output)) > MAX_OUTPUT_BYTES:
        entries.pop(0)
    if len(_encoded(output)) > MAX_OUTPUT_BYTES:
        raise ValueError("deferred_archive_too_large")
    return output, added


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review-only deferred proposal archive")
    parser.add_argument("--input", default="runtime-health/gemini-proposals.json")
    parser.add_argument("--audit", default="runtime-health/ai-batch-review-audit.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    path = Path(args.output)
    previous = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    archive, added = build_archive(source, audit, previous, os.environ.get("GITHUB_RUN_ID", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(archive, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print("ASTRA_DEFERRED_ARCHIVE=" + json.dumps({
        "added": added,
        "retained": len(archive["entries"]),
        "approval": False, "publication_triggered": False,
    }))


if __name__ == "__main__":
    main()
