"""Append history-aware plot-first drafts to the unreviewed proposal inventory.

Does not approve, reserve or publish anything.
"""
import json
import os
from pathlib import Path

from astra_v2.persisted_plot_proposals import proposals_with_history
from astra_v2.plot_first_proposals import structural_key
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.publication_quality import publication_rejection


def append_plot_first(path, limit=10, publisher_path="astra_v2_state.json",
                      story_path="astra_story_history.json"):
    if not 0 <= limit <= 100:
        raise ValueError("Invalid plot-first batch limit")
    target = Path(path)
    state = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("proposals"), list):
        raise ValueError("Invalid proposal ledger")
    existing = state["proposals"]
    if any(not isinstance(item, dict) for item in existing):
        raise ValueError("Invalid proposal entry")
    seen_ids = {item.get("content_id") for item in existing}
    seen_keys = {key for item in existing if (key := structural_key(item)) is not None}
    index = NoveltyIndex(existing)
    added = []
    # Request all finite candidates so previously inventoried drafts do not
    # permanently occupy the first page of results.
    for candidate in proposals_with_history(
            limit=100, publisher_path=publisher_path, story_path=story_path):
        key = structural_key(candidate)
        if (candidate["content_id"] in seen_ids or key in seen_keys
                or index.is_near_duplicate(candidate)):
            continue
        if candidate.get("production_ready") is not False or (
                publication_rejection(candidate) != "unreviewed_causal_draft"):
            raise ValueError("Plot-first candidate breached publication isolation")
        added.append(candidate)
        seen_ids.add(candidate["content_id"])
        seen_keys.add(key)
        index.add(candidate)
        if len(added) == limit:
            break
    if added:
        state["proposals"].extend(added)
        temp = target.with_name(target.name + ".plot-first.tmp")
        temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(temp, target)
    return len(added)


if __name__ == "__main__":
    print("ASTRA_PLOT_FIRST_UNREVIEWED_ADDED=" + str(append_plot_first(
        os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"),
        limit=int(os.getenv("ASTRA_PLOT_FIRST_BATCH", "10")))))
