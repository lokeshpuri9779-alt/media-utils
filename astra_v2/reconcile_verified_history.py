"""Reconcile verified publication metadata without inventing plot fingerprints."""
import json
from pathlib import Path
from astra_v2.verified_story_history import record_confirmed

def reconcile_verified_history(publisher_path="astra_v2_state.json",
                               history_path="astra_story_history.json"):
    state = json.loads(Path(publisher_path).read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("published"), dict):
        raise ValueError("Invalid publisher journal")
    added = 0
    skipped = 0
    for cid, item in state["published"].items():
        if not isinstance(item, dict) or not item.get("video_id") or not item.get("confirmed_at"):
            skipped += 1
            continue
        if record_confirmed(history_path, cid, item):
            added += 1
    history = json.loads(Path(history_path).read_text(encoding="utf-8"))
    entries = history["stories"] if isinstance(history, dict) else history
    return {"added": added, "skipped_unverified": skipped, "total": len(entries),
            "with_plot_fingerprint": sum(bool(x.get("plot_fingerprint")) for x in entries),
            "unknown_plot_fingerprint": sum(not bool(x.get("plot_fingerprint")) for x in entries)}

if __name__ == "__main__":
    print("ASTRA_HISTORY_RECONCILIATION=" + json.dumps(reconcile_verified_history(), sort_keys=True))
