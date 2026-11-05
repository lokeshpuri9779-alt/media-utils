"""Local, review-only triage of archived Gemini drafts; no provider calls.

Passing deterministic checks does NOT constitute editorial approval, artwork
semantic fidelity, or eligibility for publication.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from astra_v2.gemini_deferred_archive import (
    ARCHIVE_STATUS, MAX_ENTRIES, _encoded,
)


KNOWN_ISSUES = frozenset({
    "narrative_duplicate", "repeated_causal_premise",
    "insufficient_narrative_detail", "insufficient_visual_variety",
    "missing_plot_fingerprint", "not_reviewed_authored_story",
    "not_production_ready", "invalid_story",
})


def _category(value):
    """Return a fixed diagnostic category; never copy story or exception text."""
    if value in KNOWN_ISSUES:
        return value
    if value.startswith("publication_renderer_incompatible"):
        return "renderer_incompatible"
    if value.startswith("publication_"):
        return "other_publication_blocker"
    return "other_local_issue"


def triage_archive(archive, history, checker=None):
    """Summarize local blockers on exact, still-unreviewed source payloads.

    A caller-provided checker is only for offline tests; the production checker
    is ASTRA's existing candidate_issues, with the production unified renderer
    gate enabled by the invoking workflow.
    """
    if (not isinstance(archive, dict) or archive.get("version") != 1
            or archive.get("status") != ARCHIVE_STATUS
            or archive.get("publication_approval") is not False
            or archive.get("eligible_for_automatic_publishing") is not False):
        raise ValueError("invalid_deferred_archive_metadata")
    entries = archive.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError("invalid_deferred_archive_entries")
    if not isinstance(history, (list, tuple)):
        raise ValueError("complete_story_history_required")
    if checker is None:
        from astra_v2.production_story_gate import candidate_issues
        checker = candidate_issues

    results = Counter()
    categories = Counter()
    seen = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("invalid_deferred_archive_entry")
        story = item.get("proposal")
        digest = item.get("source_sha256")
        if (item.get("review_status") != "deferred_unreviewed"
                or item.get("deferred_reason") not in (
                    "review_deferred:rate_limited",
                    "review_deferred:provider_unavailable",
                    "review_deferred:timeout",
                    "review_deferred:transport_unavailable")
                or not isinstance(story, dict)
                or not isinstance(story.get("content_id"), str)
                or not story["content_id"]
                or item.get("content_id") != story["content_id"]
                or story.get("kind") != "microfiction"
                or not isinstance(digest, str)
                or len(digest) != 64
                or digest != hashlib.sha256(_encoded(story)).hexdigest()
                or digest in seen):
            raise ValueError("deferred_archive_source_mismatch")
        seen.add(digest)
        # Mirror Gemini's independent-review input normalization on a COPY.
        # Do not change the archived story or synthesize an approval record.
        candidate = dict(story)
        candidate["kind"] = "authored_causal_story"
        try:
            issues = checker(candidate, history)
            if not isinstance(issues, (list, tuple)) or any(
                    not isinstance(issue, str) for issue in issues):
                raise ValueError("invalid_local_gate_response")
            for category in set(map(_category, issues)):
                categories[category] += 1
            results["blocked" if issues else "local_checks_clear"] += 1
        except Exception:
            # A failing checker is NOT a clean pass.
            results["unavailable"] += 1

    return {
        "status": "review_only_diagnostic",
        "source_count": len(entries),
        "local_checks_clear": results["local_checks_clear"],
        "blocked": results["blocked"],
        "unavailable": results["unavailable"],
        "issue_category_counts": dict(sorted(categories.items())),
        "scope": "local_checks_only_no_provider_no_artwork_or_editorial_approval",
        "editorial_approval": False,
        "publication_triggered": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline deferred Gemini triage")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--publisher-state", default="astra_v2_state.json")
    parser.add_argument("--story-history", default="astra_story_history.json")
    args = parser.parse_args(argv)
    for path in (args.publisher_state, args.story_history):
        if not Path(path).is_file():
            raise SystemExit("Deferred triage requires complete story history")
    from astra_v2.proposal_history import load_history
    history = load_history(args.publisher_state, args.story_history)
    archive = json.loads(Path(args.archive).read_text(encoding="utf-8"))
    report = triage_archive(archive, history)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    # Summary only. Never print the proposals or model/provider secrets.
    print("ASTRA_DEFERRED_LOCAL_TRIAGE=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
