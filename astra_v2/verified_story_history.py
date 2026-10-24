"""Append verified publication identities to durable story novelty history."""
import json
import os
import tempfile
from pathlib import Path

def record_confirmed(history_path, content_id, publication):
    """Only confirmed publisher entries; never invent absent fingerprints."""
    if not isinstance(publication, dict) or not publication.get("video_id") or not publication.get("confirmed_at"):
        raise ValueError("Publication is not verified")
    path = Path(history_path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("stories") if isinstance(data, dict) else data
        if not isinstance(records, list) or any(not isinstance(x, dict) for x in records):
            raise ValueError("Invalid existing story history")
    else:
        records = []
    if any(x.get("content_id") == content_id for x in records):
        return False
    entry = {"content_id": content_id, "video_id": publication["video_id"],
             "confirmed_at": publication["confirmed_at"]}
    for key in ("title", "plot_key", "plot_fingerprint", "story_beats",
                "central_conflict", "decisive_choice", "resolution"):
        if publication.get(key):
            entry[key] = publication[key]
    records.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".astra-history-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({"stories": records}, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True
