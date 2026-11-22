"""Bound the unreviewed story-proposal ledger so editorial audits stay finite.

Triage and the production-eligibility audit re-evaluate every proposal against
the full history, so their cost grows roughly quadratically with ledger size.
On Nov 22 the ledger held 7,821 proposals and the audit exceeded its job limit.

This tool only removes the OLDEST unreviewed drafts. It never drops a proposal
that is production_ready or that has a recorded editorial review decision, it
never edits a surviving proposal, and it leaves every other ledger field
(next_index, supply_health, ...) untouched. It changes no editorial gate,
threshold or approval. Earlier ledger versions stay recoverable from the
astra-state branch history.
"""
import json
import os
from pathlib import Path

MIN_KEEP = 500       # the generator's own diversity window is the newest 500
MAX_KEEP = 20000
DEFAULT_KEEP = 2000


def protected_ids(decisions):
    """Content IDs that carry an editorial review decision."""
    ids = set()
    reviews = decisions.get("reviews") if isinstance(decisions, dict) else None
    for review in reviews if isinstance(reviews, list) else []:
        if isinstance(review, dict) and isinstance(review.get("content_id"), str):
            ids.add(review["content_id"])
    return ids


def trim_ledger(ledger, keep=DEFAULT_KEEP, protected=frozenset()):
    """Return (new_ledger, report). The input ledger is not modified."""
    if not isinstance(ledger, dict) or not isinstance(ledger.get("proposals"), list):
        raise ValueError("Invalid proposal ledger")
    if not isinstance(keep, int) or not MIN_KEEP <= keep <= MAX_KEEP:
        raise ValueError(f"keep must be an integer between {MIN_KEEP} and {MAX_KEEP}")
    proposals = ledger["proposals"]
    for story in proposals:
        if not isinstance(story, dict):
            raise ValueError("Invalid proposal")
    cutoff = max(len(proposals) - keep, 0)
    kept = []
    protected_kept = 0
    for position, story in enumerate(proposals):
        must_keep = bool(story.get("production_ready")) or story.get("content_id") in protected
        if position >= cutoff:
            kept.append(story)
        elif must_keep:
            kept.append(story)
            protected_kept += 1
    result = dict(ledger)
    result["proposals"] = kept
    report = {"before": len(proposals), "after": len(kept),
              "dropped": len(proposals) - len(kept),
              "protected_kept": protected_kept, "keep": keep}
    return result, report


def trim_file(ledger_path, decisions_path=None, keep=DEFAULT_KEEP):
    path = Path(ledger_path)
    ledger = json.loads(path.read_text(encoding="utf-8"))
    decisions = {}
    if decisions_path and Path(decisions_path).exists():
        decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    trimmed, report = trim_ledger(ledger, keep=keep, protected=protected_ids(decisions))
    if report["dropped"]:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")
        temporary.replace(path)
    return report


if __name__ == "__main__":
    try:
        keep_value = int(os.getenv("ASTRA_LEDGER_KEEP", str(DEFAULT_KEEP)))
    except ValueError:
        keep_value = DEFAULT_KEEP
    summary = trim_file(
        os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"),
        os.getenv("ASTRA_REVIEW_DECISIONS", "runtime-health/story_review_decisions.json"),
        keep=keep_value)
    print("ASTRA_LEDGER_RETENTION=" + json.dumps(summary, sort_keys=True))
