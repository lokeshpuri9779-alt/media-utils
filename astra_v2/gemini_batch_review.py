"""Independently review generated Gemini batches; never grant approval on errors."""
import argparse
import json
from pathlib import Path

from astra_v2.independent_editorial_reviewer import assess
from astra_v2.editorial_approval_manifest import story_digest


def review_batch(document, history, reviewer=assess):
    if document.get("status") != "unreviewed" or not isinstance(document.get("stories"), list):
        raise ValueError("invalid_unreviewed_batch")
    approved, decisions, audit = [], [], []
    for proposal in document["stories"]:
        # Match the live creative pipeline: generated microfiction is not an\n        # eligible authored candidate until explicitly normalized for review.\n        story = dict(proposal)\n        if story.get("kind") != "microfiction":\n            raise ValueError("unexpected_gemini_proposal_kind")\n        story["kind"] = "authored_causal_story"\n        verdict = reviewer(story, history + approved)
        record = verdict.get("record")
        accepted = verdict.get("approved") is True and isinstance(record, dict) and record.get("story_sha256") == story_digest(story)
        audit.append({"content_id": story["content_id"], "approved": accepted,
                      "issues": verdict.get("issues") or ([] if accepted else ["invalid_approval_record"])})
        if accepted:
            approved.append(story)
            decisions.append(record)
    return {"stories": approved}, {"reviews": decisions}, {"reviews": audit}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="runtime-health/gemini-proposals.json")
    parser.add_argument("--output-dir", default="runtime-health")
    args = parser.parse_args()
    from astra_v2.proposal_history import load_history
    history = load_history("astra_v2_state.json", "astra_story_history.json")
    document = json.loads(Path(args.input).read_text(encoding="utf-8"))
    stories, reviews, audit = review_batch(document, list(history))
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    for name, value in (("ai-reviewed-stories.json", stories),
                        ("ai-reviewed-decisions.json", reviews),
                        ("ai-batch-review-audit.json", audit)):
        (folder / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ASTRA_GEMINI_REVIEW=" + json.dumps({"generated": len(document["stories"]),
          "approved": len(stories["stories"]), "rejected": len(audit["reviews"]) - len(stories["stories"])}))


if __name__ == "__main__":
    main()
