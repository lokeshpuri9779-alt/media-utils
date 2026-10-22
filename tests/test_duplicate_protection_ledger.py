import json
from pathlib import Path
from astra_v2.proposal_history import load_history


def test_separate_duplicate_ledger_retains_old_publications(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("astra_v2_state.json").write_text(json.dumps({"published": {}, "reserved": {}, "pending": {}}))
    Path("astra_story_history.json").write_text('{"stories":[]}')
    Path("astra_duplicate_protection.json").write_text(json.dumps({
        "published": {"previously-uploaded": {"video_id": "verified-video"}},
        "stories": [{"content_id": "historical-story", "plot_fingerprint": "old-plot"}]
    }))
    records = load_history()
    assert any(x.get("content_id") == "previously-uploaded" for x in records)
    assert any(x.get("content_id") == "historical-story" for x in records)

def test_ledger_is_resolved_beside_custom_publisher_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    nested = tmp_path / "runtime"
    nested.mkdir()
    (nested / "state.json").write_text('{"published": {}, "pending": {}, "reserved": {}}')
    (nested / "history.json").write_text('{"stories":[]}')
    (nested / "astra_duplicate_protection.json").write_text(json.dumps({
        "published": {"older-video": {"video_id": "abc123"}},
        "stories": []
    }))
    records = load_history(nested / "state.json", nested / "history.json")
    assert any(x["content_id"] == "older-video" for x in records)
