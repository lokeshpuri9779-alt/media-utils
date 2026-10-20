"""Read-only cohort report for proposals added in the current workflow run."""
import json
from collections import Counter
from pathlib import Path


def build(ledger_path, review_path, previous_ids_path, output_path):
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    previous = set(json.loads(Path(previous_ids_path).read_text(encoding="utf-8")))
    proposals = ledger["proposals"]
    audits = review["proposals"]
    if len(proposals) != len(audits):
        raise ValueError("Proposal/audit count mismatch")
    counts = Counter()
    new_ids = set()
    for story, audit in zip(proposals, audits):
        cid = story.get("content_id")
        if cid != audit.get("content_id"):
            raise ValueError("Proposal/audit ordering mismatch")
        if cid in previous:
            continue
        if not cid or cid in new_ids:
            raise ValueError("Duplicate or missing new content ID")
        new_ids.add(cid)
        if story.get("production_ready") is not False:
            raise ValueError("New proposal must remain unapproved")
        counts.update(audit.get("editorial_issues") or [])
    result = {
        "schema_version": 1,
        "previous_inventory": len(previous),
        "current_inventory": len(proposals),
        "new_proposals": len(new_ids),
        "new_editorial_reason_counts": dict(sorted(counts.items())),
        "approved_for_production": 0,
        "publication_enabled": False,
        "note": "Current-run cohort only; historical proposals excluded. Flags are not semantic quality scores.",
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(
        "runtime-health/story_proposals.json",
        "runtime-health/story_supply_review.json",
        "/tmp/astra-plot-first-before.json",
        "runtime-health/story_new_cohort_quality.json",
    ), sort_keys=True))
