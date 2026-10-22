"""Read publication identities for non-publishing proposal novelty checks."""
import json
from pathlib import Path


def load_history(publisher_path="astra_v2_state.json", story_path="astra_story_history.json"):
    """Missing optional files are allowed; malformed present files fail closed."""
    records = []
    publisher = Path(publisher_path)
    if publisher.exists():
        state = json.loads(publisher.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("Invalid publisher state")
        for bucket in ("published", "pending", "reserved", "rejected"):
            items = state.get(bucket, {})
            if not isinstance(items, dict):
                raise ValueError("Invalid publisher history bucket: " + bucket)
            for cid, item in items.items():
                if not isinstance(item, dict):
                    records.append({"content_id": str(cid)})
                else:
                    records.append({"content_id": str(item.get("content_id") or cid), **item})
    history_file = Path(story_path)
    if history_file.exists():
        data = json.loads(history_file.read_text(encoding="utf-8"))
        stories = data.get("stories", []) if isinstance(data, dict) else data
        if not isinstance(stories, list):
            raise ValueError("Invalid story history")
        if any(not isinstance(item, dict) for item in stories):
            raise ValueError("Invalid story history entry")
        records.extend(stories)
    protection = Path("astra_duplicate_protection.json")
    if protection.exists():
        ledger = json.loads(protection.read_text(encoding="utf-8"))
        if not isinstance(ledger, dict) or not isinstance(ledger.get("published"), dict) or not isinstance(ledger.get("stories"), list):
            raise ValueError("Invalid duplicate protection ledger")
        for cid, item in ledger["published"].items():
            if not isinstance(item, dict):
                raise ValueError("Invalid protected publication")
            records.append({"content_id": str(cid), **item})
        if any(not isinstance(item, dict) for item in ledger["stories"]):
            raise ValueError("Invalid protected story history")
        records.extend(ledger["stories"])
    return records
