"""Generate a non-publishing editorial report for queued story proposals."""
import json
import os
from pathlib import Path
from astra_v2.story_editorial import triage


def report(ledger_path, output_path, history=()):
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    proposals = ledger.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError("Invalid proposal ledger")
    result = triage(proposals, history=history, use_semantic_index=True)
    result["total_proposals"] = len(proposals)
    result["requires_editorial_review"] = sum(
        bool(item.get("awaiting_editorial_decision"))
        for item in result["ready_for_review"] + result["needs_work"]
    )
    result["automatic_publication_enabled"] = False
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    from astra_v2.proposal_history import load_history
    summary = report(
        os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"),
        os.getenv("ASTRA_EDITORIAL_REPORT", "runtime-health/story_editorial_report.json"),
        history=load_history())
    print("ASTRA_EDITORIAL_PROPOSALS=" + str(summary["total_proposals"]))
    print("ASTRA_EDITORIAL_REVIEW_REQUIRED=" + str(summary["requires_editorial_review"]))
