"""Offline, human-reviewed story promotion. Never changes production automatically."""
import argparse
import json
from pathlib import Path

from astra_v2.story_forge import catalog, plot_fingerprint
from astra_v2.story_expansion_2000 import candidate_records


def promote(approvals):
    if not isinstance(approvals, list):
        raise ValueError("approvals_must_be_list")
    candidates = {key: (title, genre, beats) for key, title, genre, beats in candidate_records()}
    existing = catalog(limit=10000)
    fingerprints = {x["plot_fingerprint"] for x in existing}
    titles = {x["title"].casefold().strip() for x in existing}
    used = set()
    output = []
    for approval in approvals:
        if not isinstance(approval, dict):
            raise ValueError("invalid_approval")
        key = approval.get("key")
        reviewer = approval.get("reviewer")
        reason = approval.get("editorial_reason")
        fingerprint = approval.get("plot_fingerprint")
        if not all(isinstance(v, str) and v.strip() for v in (key, reviewer, reason, fingerprint)):
            raise ValueError("missing_review_evidence")
        if len(reason.strip().split()) < 8:
            raise ValueError("editorial_reason_too_short")
        if key not in candidates or key in used:
            raise ValueError("unknown_or_duplicate_candidate")
        title, genre, beats = candidates[key]
        actual = plot_fingerprint(beats)
        if fingerprint != actual:
            raise ValueError("candidate_fingerprint_mismatch")
        if actual in fingerprints or title.casefold().strip() in titles:
            raise ValueError("already_published_or_approved")
        used.add(key)
        fingerprints.add(actual)
        titles.add(title.casefold().strip())
        output.append([key, title, genre, beats])
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approvals", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    approvals = json.loads(Path(args.approvals).read_text(encoding="utf-8"))
    reviewed = promote(approvals)
    if not reviewed:
        raise ValueError("no_reviewed_stories")
    # Generated file must be code-reviewed and explicitly imported into story_forge.
    # Merely running this tool never makes a story production-ready.
    Path(args.output).write_text(
        '"""Explicitly reviewed ASTRA stories. Requires separate production integration."""\n'
        + "PLOTS = " + repr(reviewed) + "\n", encoding="utf-8")
    print(f"Prepared {len(reviewed)} reviewed stories for separate PR review; none published.")


if __name__ == "__main__":
    main()
