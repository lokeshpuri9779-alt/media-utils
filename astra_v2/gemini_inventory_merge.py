"""Merge independently approved batches without losing prior unconsumed approvals."""
import json
from pathlib import Path
from astra_v2.editorial_approved_intake import approved_intake
from astra_v2.proposal_history import load_history


def merge_inventory(old_stories, old_reviews, new_stories, new_reviews, history):
    if len(old_stories) != len(old_reviews) or len(new_stories) != len(new_reviews):
        raise ValueError("inventory_pair_length_mismatch")
    # Validate both manifests against current publication history. Published
    # entries are pruned rather than reintroduced into the ready queue.
    previous = approved_intake(old_stories, old_reviews, history)
    incoming = approved_intake(new_stories, new_reviews, history)
    prior_records = {r["content_id"]: r for r in old_reviews}
    new_records = {r["content_id"]: r for r in new_reviews}
    output, records, seen = [], [], set()
    for story, record in [(s, prior_records[s["content_id"]]) for s in previous["stories"]] + [
        (s, new_records[s["content_id"]]) for s in incoming["stories"]]:
        cid = story["content_id"]
        if cid in seen:
            continue
        seen.add(cid)
        output.append(story)
        records.append(record)
    # Enforce cross-batch novelty, hashes, and complete-history validation.
    validated = approved_intake(output, records, history)
    accepted = {s["content_id"] for s in validated["stories"]}
    return {"stories": [s for s in output if s["content_id"] in accepted]}, {
        "reviews": [r for r in records if r["content_id"] in accepted]}


def main():
    root = Path("runtime-health")
    state = Path(__import__("sys").argv[1])
    history = load_history("astra_v2_state.json", "astra_story_history.json")
    def read(path, key):
        return json.loads(path.read_text(encoding="utf-8"))[key] if path.is_file() else []
    old_s = state / "ai-reviewed-stories.json"
    old_r = state / "ai-reviewed-decisions.json"
    if old_s.exists() != old_r.exists():
        raise ValueError("incomplete_persisted_approval_pair")
    stories, reviews = merge_inventory(read(old_s, "stories"), read(old_r, "reviews"),
        read(root / "ai-reviewed-stories.json", "stories"),
        read(root / "ai-reviewed-decisions.json", "reviews"), history)
    (state / "ai-reviewed-stories.json").write_text(json.dumps(stories, indent=2) + "\n")
    (state / "ai-reviewed-decisions.json").write_text(json.dumps(reviews, indent=2) + "\n")
    print("ASTRA_CUMULATIVE_APPROVED=" + str(len(stories["stories"])))


if __name__ == "__main__":
    main()
