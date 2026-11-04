"""Independently review generated Gemini batches; never grant approval on errors."""
import argparse
import json
from pathlib import Path

from astra_v2.independent_editorial_reviewer import assess
from astra_v2.editorial_approval_manifest import story_digest



def review_outage_category(issues):
    """Recognize only known temporary provider errors, not editorial decisions."""
    if not isinstance(issues, (tuple, list)):
        return None
    if ("review_failed:HTTP_429" in issues
            or "review_provider:rate_limited" in issues):
        return "rate_limited"
    if ("review_provider:provider_unavailable" in issues
            or any(item in issues for item in (
                "review_failed:HTTP_500", "review_failed:HTTP_502",
                "review_failed:HTTP_503", "review_failed:HTTP_504"))):
        return "provider_unavailable"
    if "review_failed:TimeoutError" in issues:
        return "timeout"
    if "review_failed:URLError" in issues:
        return "transport_unavailable"
    return None


def deferred_review_count(rows):
    """Count every nondecision, including the triggering failed review."""
    return sum(any(str(issue).startswith("review_deferred:")
                   for issue in row.get("issues", []))
               for row in rows if isinstance(row, dict))


def review_batch(document, history, reviewer=assess):
    if document.get("status") != "unreviewed" or not isinstance(document.get("stories"), list):
        raise ValueError("invalid_unreviewed_batch")
    approved, decisions, audit = [], [], []
    outage = None
    for proposal in document["stories"]:
        # Normalize generated microfiction before independent editorial review.
        story = dict(proposal)
        if story.get("kind") != "microfiction":
            raise ValueError("unexpected_gemini_proposal_kind")
        story["kind"] = "authored_causal_story"
        if outage is not None:
            # A temporary provider outage is not an editorial verdict.
            # Keep the original proposal in the unreviewed batch artifact.
            audit.append({"content_id": story["content_id"], "approved": False,
                          "issues": ["review_deferred:" + outage]})
            continue
        verdict = reviewer(story, history + approved)
        issues = list(verdict.get("issues") or [])
        outage = review_outage_category(issues)
        if outage is not None:
            # Record the triggering request as deferred, too. Never relabel
            # provider failure as a creative/editorial rejection.
            issues.append("review_deferred:" + outage)
        record = verdict.get("record")
        accepted = (outage is None and verdict.get("approved") is True
                    and isinstance(record, dict)
                    and record.get("story_sha256") == story_digest(story))
        audit.append({"content_id": story["content_id"], "approved": accepted,
                      "issues": issues or ([] if accepted else ["invalid_approval_record"])})
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
    deferred = deferred_review_count(audit["reviews"])
    print("ASTRA_GEMINI_REVIEW=" + json.dumps({
        "generated": len(document["stories"]),
        "reviewed": len(audit["reviews"]) - deferred,
        "approved": len(stories["stories"]),
        "rejected": len(audit["reviews"]) - len(stories["stories"]) - deferred,
        "deferred": deferred,
    }))


if __name__ == "__main__":
    main()
