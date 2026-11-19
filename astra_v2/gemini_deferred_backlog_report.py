"""Provider-free ranking of archived Gemini drafts for human review.

Requires the retry-ledger contract introduced in PR #1008.

This diagnostic composes the existing archive validator, local triage gate and
retry eligibility ledger. It does not call a model, consume retry attempts,
approve a story, or feed publisher intake.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from astra_v2.gemini_deferred_archive import ARCHIVE_STATUS
from astra_v2.gemini_deferred_retry_queue import (
    DEFAULT_COOLDOWN_SECONDS,
    prepare_retry_batch,
)
from astra_v2.gemini_deferred_triage import triage_archive


REPORT_STATUS = "deferred_backlog_review_only"


def build_backlog_report(archive, history, retry_state=None, *, now,
                         cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
                         max_attempts=2, limit=10, checker=None):
    """Rank drafts using deterministic local evidence and retry eligibility.

    Ranking is diagnostic: retry-eligible items come first, then local checks
    that are clear, then fewer distinct blocker categories, preserving archive
    order as the final stable tie-breaker. A clear local check is not approval.
    """
    if (not isinstance(archive, dict) or archive.get("version") != 1
            or archive.get("status") != ARCHIVE_STATUS
            or archive.get("publication_approval") is not False
            or archive.get("eligible_for_automatic_publishing") is not False):
        raise ValueError("invalid_deferred_archive_metadata")
    entries = archive.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_deferred_archive_entries")

    # Prepare the bounded review batch once, then test eligibility per source
    # independently so the queue's batch limit is not mistaken for cooldown.
    queue, next_state = prepare_retry_batch(
        archive, retry_state, now=now, cooldown_seconds=cooldown_seconds,
        max_attempts=max_attempts, limit=limit,
    )
    ranked = []
    totals = Counter()
    for index, item in enumerate(entries):
        single = dict(archive)
        single["entries"] = [item]
        diagnostic = triage_archive(single, history, checker=checker)
        digest = item["source_sha256"]
        one_queue, _ = prepare_retry_batch(
            single, retry_state, now=now, cooldown_seconds=cooldown_seconds,
            max_attempts=max_attempts, limit=1,
        )
        is_eligible = one_queue["selected_count"] == 1
        categories = diagnostic["issue_category_counts"]
        local_status = (
            "clear" if diagnostic["local_checks_clear"] == 1 else
            "blocked" if diagnostic["blocked"] == 1 else "unavailable"
        )
        blockers = sorted(categories)
        row = {
            "rank": 0,
            "source_order": index + 1,
            "source_sha256": digest,
            "content_id": item["content_id"],
            "source_run_id": item.get("source_run_id", ""),
            "deferred_reason": item["deferred_reason"],
            "retry_eligible": is_eligible,
            "attempts_so_far": next(
                (x["attempts"] for x in next_state["entries"]
                 if x["source_sha256"] == digest), 0
            ),
            "local_check_status": local_status,
            "blocker_categories": blockers,
            "blocker_category_count": len(blockers),
            "review_priority": "higher" if is_eligible and local_status == "clear"
                               else "normal" if is_eligible
                               else "wait_or_resolve_blockers",
        }
        ranked.append(row)
        totals[local_status] += 1
        for category in blockers:
            totals["blocker:" + category] += 1

    ranked.sort(key=lambda row: (
        not row["retry_eligible"],
        row["local_check_status"] != "clear",
        row["blocker_category_count"],
        row["source_order"],
    ))
    for position, row in enumerate(ranked, 1):
        row["rank"] = position

    return {
        "version": 1,
        "status": REPORT_STATUS,
        "generated_at": now,
        "source_count": len(entries),
        "retry_eligible_count": sum(row["retry_eligible"] for row in ranked),
        "local_checks_clear_count": totals["clear"],
        "locally_blocked_count": totals["blocked"],
        "local_check_unavailable_count": totals["unavailable"],
        "blocker_category_counts": {
            key.removeprefix("blocker:"): value
            for key, value in sorted(totals.items())
            if key.startswith("blocker:")
        },
        "ranking": ranked,
        "scope": "local_diagnostics_and_retry_cooldown_only",
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_approval": False,
        "eligible_for_automatic_publishing": False,
        "publication_triggered": False,
    }, next_state


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Provider-free deferred Gemini backlog diagnostic")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--now", type=int, required=True,
                        help="Explicit Unix timestamp; no implicit system clock")
    parser.add_argument("--cooldown-seconds", type=int,
                        default=DEFAULT_COOLDOWN_SECONDS)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)

    archive = json.loads(Path(args.archive).read_text(encoding="utf-8"))
    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else None
    publisher_state = Path("astra_v2_state.json")
    story_history = Path("astra_story_history.json")
    if not publisher_state.is_file() or not story_history.is_file():
        raise SystemExit("Deferred backlog report requires complete story history")
    from astra_v2.proposal_history import load_history
    history = load_history(str(publisher_state), str(story_history))
    report, next_state = build_backlog_report(
        archive, history, state, now=args.now,
        cooldown_seconds=args.cooldown_seconds,
        max_attempts=args.max_attempts, limit=args.limit,
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(next_state, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print("ASTRA_DEFERRED_BACKLOG=" + json.dumps({
        "source_count": report["source_count"],
        "retry_eligible": report["retry_eligible_count"],
        "local_checks_clear": report["local_checks_clear_count"],
        "blocked": report["locally_blocked_count"],
        "unavailable": report["local_check_unavailable_count"],
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_triggered": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
