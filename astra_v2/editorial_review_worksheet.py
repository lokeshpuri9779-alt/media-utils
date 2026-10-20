"""Generate a readable, non-approving editorial worksheet from persisted shortlist exports."""
import argparse
import json
from pathlib import Path

from astra_v2.editorial_approval_manifest import story_digest


def build_worksheet(story_doc, decision_doc):
    stories = story_doc.get("stories")
    decisions = decision_doc.get("reviews")
    if not isinstance(stories, list) or not isinstance(decisions, list):
        raise ValueError("invalid_review_exports")
    if len(stories) != len(decisions) or len(stories) > 100:
        raise ValueError("review_export_count_mismatch")
    by_id = {}
    for decision in decisions:
        if not isinstance(decision, dict) or not isinstance(decision.get("content_id"), str):
            raise ValueError("invalid_decision")
        cid = decision["content_id"]
        if cid in by_id or decision.get("decision") != "pending":
            raise ValueError("worksheet_requires_unique_pending_decisions")
        by_id[cid] = decision
    lines = ["# ASTRA Editorial Review Worksheet", "",
             "This is a **read-only review aid**, not an approval record. Revise stories substantively,",
             "recompute their SHA-256 digests, and obtain explicit editorial decisions before promotion.",
             "No story in this worksheet is eligible for automatic publishing.", ""]
    seen = set()
    for index, story in enumerate(stories, 1):
        if not isinstance(story, dict):
            raise ValueError("invalid_story")
        cid = story.get("content_id")
        if not isinstance(cid, str) or cid in seen or cid not in by_id:
            raise ValueError("invalid_or_duplicate_story_id")
        seen.add(cid)
        if story.get("production_ready") is not False or story.get("kind") != "unreviewed_causal_draft":
            raise ValueError("worksheet_requires_unreviewed_drafts")
        if by_id[cid].get("story_sha256") != story_digest(story):
            raise ValueError("review_export_digest_mismatch")
        title = str(story.get("title", "Untitled")).replace("\n", " ").replace("#", "")
        lines += [f"## {index}. {title}", "", f"- Content ID: \`{cid}\`",
                  f"- Original digest: \`{story_digest(story)}\`",
                  "- Status: pending; substantive rewrite required", "",
                  "### Original narration", ""]
        for beat in story.get("story_beats", []):
            if not isinstance(beat, dict):
                continue
            name = str(beat.get("story_beat", "beat")).replace("\n", " ")
            speech = str(beat.get("speech", "")).replace("\n", " ")
            visual = str(beat.get("visual", "")).replace("\n", " ")
            lines += [f"**{name}:** {speech}", f"*Visual:* {visual}", ""]
        lines += ["### Reviewer checklist", "",
                  "- [ ] Rewrite weak causal transitions, dialogue and resolution",
                  "- [ ] Verify originality against published and reserved history",
                  "- [ ] Verify distinct, legible 9:16 visual scenes",
                  "- [ ] Verify narration and visual continuity",
                  "- [ ] Record reviewer, detailed notes and digest of final revised story", ""]
    if seen != set(by_id):
        raise ValueError("unmatched_review_decisions")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.unlink(missing_ok=True)
    content = build_worksheet(
        json.loads(Path(args.stories).read_text(encoding="utf-8")),
        json.loads(Path(args.decisions).read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print("ASTRA_EDITORIAL_WORKSHEET=" + json.dumps({
        "stories": content.count("### Reviewer checklist"), "approved": 0,
        "publication_triggered": False}))


if __name__ == "__main__":
    main()
