"""Generate a review packet from authored stories; never approve automatically."""
import argparse
import json
from pathlib import Path
from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.production_story_gate import candidate_issues


def build_packet(stories, history=()):
    if not isinstance(stories, list):
        raise ValueError("Expected list of authored stories")
    items = []
    seen_ids = set()
    for story in stories:
        if not isinstance(story, dict) or not story.get("content_id"):
            raise ValueError("Invalid story")
        content_id = story["content_id"]
        if content_id in seen_ids:
            raise ValueError("Duplicate content ID")
        seen_ids.add(content_id)
        issues = candidate_issues(story, history)
        items.append({
            "content_id": content_id,
            "title": story.get("title"),
            "kind": story.get("kind"),
            "story_sha256": story_digest(story),
            "candidate_issues": issues,
            "reviewable": not issues,
            "story_beats": story.get("story_beats", []),
            "review_template": {
                "content_id": content_id,
                "story_sha256": story_digest(story),
                "decision": "pending",
                "reviewer": "",
                "review_notes": "",
            },
        })
    return {"items": items, "reviewable_count": sum(i["reviewable"] for i in items),
            "approved_count": 0, "publication_triggered": False}


def shortlist_stories(proposals, report):
    """Resolve a diagnostic shortlist to unchanged, content-bound full drafts."""
    if not isinstance(proposals, list) or not isinstance(report, dict):
        raise ValueError("Invalid shortlist source")
    candidates = report.get("review_candidates")
    if (not isinstance(candidates, list) or len(candidates) > 100
            or report.get("candidate_count") != len(candidates)
            or report.get("source_proposal_count") != len(proposals)
            or report.get("approved_for_production") != 0
            or report.get("publication_enabled") is not False):
        raise ValueError("Invalid or publication-enabled shortlist")
    by_id = {}
    for story in proposals:
        cid = story.get("content_id") if isinstance(story, dict) else None
        if not isinstance(cid, str) or not cid.strip() or cid in by_id:
            raise ValueError("Invalid or duplicate source story ID")
        by_id[cid] = story
    selected = []
    seen = set()
    for candidate in candidates:
        cid = candidate.get("content_id") if isinstance(candidate, dict) else None
        if not isinstance(cid, str) or cid not in by_id or cid in seen:
            raise ValueError("Unknown or duplicate shortlist story ID")
        story = by_id[cid]
        if candidate.get("story_sha256") != story_digest(story):
            raise ValueError("Shortlist story digest mismatch; regenerate the shortlist")
        if (story.get("production_ready") is not False
                or candidate.get("production_ready") is not False
                or candidate.get("eligible_for_automatic_publishing") is not False):
            raise ValueError("Shortlist export cannot promote stories")
        seen.add(cid)
        selected.append(story)
    return selected


def export_packet(stories, output_path, stories_output=None, reviews_output=None):
    """Export full stories and pending decisions in the existing intake schemas."""
    if (stories_output is None) != (reviews_output is None):
        raise ValueError("Both story and review output paths are required")
    outputs = [Path(output_path)]
    if stories_output is not None:
        outputs += [Path(stories_output), Path(reviews_output)]
    if len({path.resolve() for path in outputs}) != len(outputs):
        raise ValueError("Review bundle output paths must be distinct")
    # Discard previous exports before rebuilding this packet.
    for path in outputs:
        path.unlink(missing_ok=True)
    packet = build_packet(stories)
    documents = [packet]
    if stories_output is not None:
        documents += [{"stories": stories},
                      {"reviews": [item["review_template"] for item in packet["items"]]}]
    for path, document in zip(outputs, documents):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return packet


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--shortlist", help="Resolve full proposals using a digest-bound shortlist")
    parser.add_argument("--stories-output")
    parser.add_argument("--reviews-output")
    args = parser.parse_args()
    source = json.loads(Path(args.stories).read_text(encoding="utf-8"))
    stories = (shortlist_stories(source["proposals"], json.loads(
        Path(args.shortlist).read_text(encoding="utf-8"))) if args.shortlist else source["stories"])
    result = export_packet(stories, args.output, args.stories_output, args.reviews_output)
    print("ASTRA_EDITORIAL_PACKET=" + json.dumps({
        "count": len(result["items"]), "reviewable_count": result["reviewable_count"],
        "approved_count": 0, "publication_triggered": False}))
