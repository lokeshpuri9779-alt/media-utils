"""Provider-free, review-only retry eligibility for deferred Gemini drafts.

No model or network calls are made here. Queue selection never increments
attempts. A future provider adapter may record an attempt only after it has
actually sent a provider request. This state is not editorial approval or
publisher intake.
"""
import argparse
import hashlib
import json
from pathlib import Path

from astra_v2.gemini_deferred_archive import (
    ARCHIVE_STATUS, MAX_ENTRIES, MAX_PROPOSAL_BYTES, _encoded,
)

DEFERRED_REASONS = frozenset({
    "review_deferred:rate_limited",
    "review_deferred:provider_unavailable",
    "review_deferred:timeout",
    "review_deferred:transport_unavailable",
})
STATE_STATUS = "retry_tracking_only"
QUEUE_STATUS = "retry_queue_review_only"
MAX_ATTEMPTS = 2
DEFAULT_COOLDOWN_SECONDS = 6 * 60 * 60
MAX_TRACKED_ENTRIES = 1000
MAX_QUEUE_LIMIT = 10


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("invalid_" + name)
    return value


def _validate_archive(archive):
    if (not isinstance(archive, dict) or archive.get("version") != 1
            or archive.get("status") != ARCHIVE_STATUS
            or archive.get("publication_approval") is not False
            or archive.get("eligible_for_automatic_publishing") is not False):
        raise ValueError("invalid_deferred_archive_metadata")
    entries = archive.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError("invalid_deferred_archive_entries")
    seen = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("invalid_deferred_archive_entry")
        story = item.get("proposal")
        digest = item.get("source_sha256")
        if (item.get("review_status") != "deferred_unreviewed"
                or not isinstance(item.get("deferred_reason"), str)
                or item.get("deferred_reason") not in DEFERRED_REASONS
                or not isinstance(story, dict)
                or story.get("kind") != "microfiction"
                or not isinstance(story.get("content_id"), str)
                or not story["content_id"]
                or item.get("content_id") != story["content_id"]
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)
                or digest != hashlib.sha256(_encoded(story)).hexdigest()
                or len(_encoded(story)) > MAX_PROPOSAL_BYTES
                or digest in seen):
            raise ValueError("deferred_archive_source_mismatch")
        seen.add(digest)
    return entries


def empty_retry_state():
    """Return a fresh, explicitly non-provider, non-approval tracking ledger."""
    return {
        "version": 1,
        "status": STATE_STATUS,
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_approval": False,
        "eligible_for_automatic_publishing": False,
        "entries": [],
    }


def _validate_state(state):
    if (not isinstance(state, dict) or state.get("version") != 1
            or state.get("status") != STATE_STATUS
            or state.get("provider_requests_enabled") is not False
            or state.get("editorial_approval") is not False
            or state.get("publication_approval") is not False
            or state.get("eligible_for_automatic_publishing") is not False):
        raise ValueError("invalid_retry_tracking_state")
    entries = state.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_TRACKED_ENTRIES:
        raise ValueError("invalid_retry_tracking_entries")
    by_hash = {}
    for row in entries:
        if not isinstance(row, dict):
            raise ValueError("invalid_retry_tracking_entry")
        digest = row.get("source_sha256")
        content_id = row.get("content_id")
        attempts = row.get("attempts")
        first_seen_at = row.get("first_seen_at")
        last_attempt_at = row.get("last_attempt_at")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)
                or not isinstance(content_id, str) or not content_id
                or isinstance(attempts, bool) or not isinstance(attempts, int)
                or attempts < 0 or attempts > MAX_ATTEMPTS
                or isinstance(first_seen_at, bool)
                or not isinstance(first_seen_at, int) or first_seen_at < 0
                or (attempts == 0 and last_attempt_at is not None)
                or (attempts > 0 and (
                    isinstance(last_attempt_at, bool)
                    or not isinstance(last_attempt_at, int)
                    or last_attempt_at < first_seen_at))
                or digest in by_hash):
            raise ValueError("invalid_retry_tracking_entry")
        by_hash[digest] = {
            "source_sha256": digest,
            "content_id": content_id,
            "attempts": attempts,
            "first_seen_at": first_seen_at,
            "last_attempt_at": last_attempt_at,
        }
    return by_hash


def prepare_retry_batch(archive, state=None, *, now,
                        cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
                        max_attempts=MAX_ATTEMPTS, limit=5):
    """Return a review-only queue and next ledger; selection consumes no attempt.

    The caller supplies an explicit Unix timestamp for deterministic dry runs.
    """
    now = _integer(now, "now")
    cooldown_seconds = _integer(cooldown_seconds, "cooldown_seconds")
    max_attempts = _integer(max_attempts, "max_attempts", minimum=1)
    limit = _integer(limit, "limit", minimum=1)
    if max_attempts > MAX_ATTEMPTS:
        raise ValueError("max_attempts_exceeds_safety_ceiling")
    if limit > MAX_QUEUE_LIMIT:
        raise ValueError("retry_queue_limit_exceeds_safety_ceiling")

    archive_entries = _validate_archive(archive)
    if state is None:
        state = empty_retry_state()
    tracked = _validate_state(state)

    # Copy existing tracking records. New source hashes start at zero attempts.
    next_entries = list(tracked.values())
    by_hash = dict(tracked)
    for item in archive_entries:
        digest = item["source_sha256"]
        existing = by_hash.get(digest)
        if existing is not None:
            if existing["content_id"] != item["content_id"]:
                raise ValueError("retry_tracking_identity_mismatch")
            continue
        row = {
            "source_sha256": digest,
            "content_id": item["content_id"],
            "attempts": 0,
            "first_seen_at": now,
            "last_attempt_at": None,
        }
        by_hash[digest] = row
        next_entries.append(row)
    if len(next_entries) > MAX_TRACKED_ENTRIES:
        raise ValueError("retry_tracking_state_too_large")

    selected = []
    for item in archive_entries:
        record = by_hash[item["source_sha256"]]
        attempts = record["attempts"]
        if attempts >= max_attempts:
            continue
        last_attempt_at = record["last_attempt_at"]
        cooldown_anchor = last_attempt_at if last_attempt_at is not None else record["first_seen_at"]
        if now - cooldown_anchor < cooldown_seconds:
            continue
        selected.append({
            "source_sha256": item["source_sha256"],
            "content_id": item["content_id"],
            "deferred_reason": item["deferred_reason"],
            "attempts_so_far": attempts,
            "last_attempt_at": last_attempt_at,
            "proposal": item["proposal"],
        })
        if len(selected) >= limit:
            break

    next_state = {
        "version": 1,
        "status": STATE_STATUS,
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_approval": False,
        "eligible_for_automatic_publishing": False,
        "entries": next_entries,
    }
    queue = {
        "version": 1,
        "status": QUEUE_STATUS,
        "generated_at": now,
        "cooldown_seconds": cooldown_seconds,
        "max_attempts": max_attempts,
        "selected_count": len(selected),
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_approval": False,
        "eligible_for_automatic_publishing": False,
        "entries": selected,
    }
    return queue, next_state


def record_attempts_after_provider_call(state, source_hashes, *, attempted_at,
                                        cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
                                        max_attempts=MAX_ATTEMPTS):
    """Record attempts only after an adapter has actually dispatched requests.

    This function itself performs no provider request. Never call it for queue
    selection, dry runs, local validation, or failures before request dispatch.
    """
    attempted_at = _integer(attempted_at, "attempted_at")
    cooldown_seconds = _integer(cooldown_seconds, "cooldown_seconds")
    max_attempts = _integer(max_attempts, "max_attempts", minimum=1)
    if max_attempts > MAX_ATTEMPTS:
        raise ValueError("max_attempts_exceeds_safety_ceiling")
    if (not isinstance(source_hashes, (list, tuple)) or not source_hashes
            or any(not isinstance(value, str) for value in source_hashes)
            or len(set(source_hashes)) != len(source_hashes)):
        raise ValueError("invalid_attempt_source_hashes")

    tracked = _validate_state(state)
    updated = dict(tracked)
    for digest in source_hashes:
        row = updated.get(digest)
        if row is None:
            raise ValueError("unknown_retry_source_hash")
        if row["attempts"] >= max_attempts:
            raise ValueError("retry_attempt_limit_reached")
        previous = row["last_attempt_at"]
        if attempted_at < row["first_seen_at"]:
            raise ValueError("retry_cooldown_not_elapsed")
        if previous is not None:
            if attempted_at < previous or attempted_at - previous < cooldown_seconds:
                raise ValueError("retry_cooldown_not_elapsed")
        updated[digest] = {
            "source_sha256": digest,
            "content_id": row["content_id"],
            "attempts": row["attempts"] + 1,
            "first_seen_at": row["first_seen_at"],
            "last_attempt_at": attempted_at,
        }

    return {
        "version": 1,
        "status": STATE_STATUS,
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_approval": False,
        "eligible_for_automatic_publishing": False,
        "entries": list(updated.values()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare a provider-free Gemini retry eligibility queue")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--now", type=int, required=True,
                        help="Explicit Unix timestamp; no implicit system clock")
    parser.add_argument("--cooldown-seconds", type=int, default=DEFAULT_COOLDOWN_SECONDS)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    archive = json.loads(Path(args.archive).read_text(encoding="utf-8"))
    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else None
    queue, next_state = prepare_retry_batch(
        archive, state, now=args.now, cooldown_seconds=args.cooldown_seconds,
        max_attempts=args.max_attempts, limit=args.limit,
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(next_state, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    output_path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print("ASTRA_DEFERRED_RETRY_QUEUE=" + json.dumps({
        "selected": queue["selected_count"],
        "tracked": len(next_state["entries"]),
        "provider_requests_enabled": False,
        "editorial_approval": False,
        "publication_triggered": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
