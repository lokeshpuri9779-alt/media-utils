"""Read-only guard for a separate text-only editorial review queue."""
import json
from pathlib import Path

from astra_v2.story_factory_rewrite_queue import reusable_pending_queue


def refresh_decision(path):
    """Allow one text-only rewrite batch; never overwrite an unreviewed queue."""
    target = Path(path)
    if not target.exists():
        return True, "no_pending_text_review"
    try:
        queue = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError("existing_text_review_queue_unreadable") from exc
    if not reusable_pending_queue(queue):
        raise ValueError("existing_text_review_queue_requires_manual_recovery")
    return False, "existing_text_review_queue_preserved"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    refresh, reason = refresh_decision(args.path)
    print(json.dumps({"refresh": refresh, "reason": reason}))
