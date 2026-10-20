"""Compare new and historical story cohorts without changing editorial decisions."""
import json
from collections import Counter
from pathlib import Path


def compare(ledger, review, existing_ids):
    stories = ledger["proposals"]
    audits = review["proposals"]
    if len(stories) != len(audits):
        raise ValueError("Proposal/audit count mismatch")
    cohorts = {"new": Counter(), "historical": Counter()}
    seen = set()
    for story, audit in zip(stories, audits):
        identity = story["content_id"]
        if identity in seen or identity != audit.get("content_id"):
            raise ValueError("Duplicate or mismatched proposal identity")
        seen.add(identity)
        stats = cohorts["historical" if identity in existing_ids else "new"]
        stats["total"] += 1
        for issue in set(audit.get("editorial_issues") or []):
            stats["issue:" + issue] += 1
        if audit.get("publication_rejection"):
            stats["publication_blocked"] += 1
    return {
        "schema_version": 1,
        "new": dict(cohorts["new"]),
        "historical": dict(cohorts["historical"]),
        "approved_for_production": 0,
        "publication_enabled": False,
    }


def main():
    ledger = json.loads(Path("runtime-health/story_proposals.json").read_text())
    review = json.loads(Path("runtime-health/story_supply_review.json").read_text())
    existing = set(json.loads(Path("/tmp/astra-existing-proposal-ids.json").read_text()))
    result = compare(ledger, review, existing)
    Path("runtime-health/story_cohort_quality.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("ASTRA_STORY_COHORT_QUALITY=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
