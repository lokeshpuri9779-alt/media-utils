"""Reviewed authored narratives retain source approval and correct QA genre."""
import json
from pathlib import Path
import pytest
from astra_v2.editorial_creative_source import load_editorial_stories


def test_approved_authored_story_is_fiction_after_intake(monkeypatch, tmp_path):
    from astra_v2 import editorial_approved_intake as intake
    monkeypatch.setattr(intake, "approved_intake", lambda *args: {"intake_count": 1, "stories": [
        {"content_id": "approved-1", "kind": "authored_causal_story", "story_beats": [{"speech": "A bell rings.", "visual": "signal_bell"}]}]})
    from astra_v2 import proposal_history
    monkeypatch.setattr(proposal_history, "load_history", lambda *args: ())
    for name in ("stories.json", "reviews.json", "state.json", "history.json"):
        (tmp_path / name).write_text(json.dumps({"stories": [], "reviews": []}))
    for key, name in (("ASTRA_EDITORIAL_STORIES_FILE", "stories.json"), ("ASTRA_EDITORIAL_REVIEWS_FILE", "reviews.json"), ("ASTRA_PUBLISHER_STATE_PATH", "state.json"), ("ASTRA_STORY_HISTORY_PATH", "history.json")):
        monkeypatch.setenv(key, str(tmp_path / name))
    result = load_editorial_stories()
    assert result[0]["genre"] == "fiction"
    assert result[0]["content_id"] == "approved-1"


def test_non_narrative_reviewed_story_keeps_genre(monkeypatch, tmp_path):
    from astra_v2 import editorial_approved_intake as intake
    monkeypatch.setattr(intake, "approved_intake", lambda *args: {"intake_count": 1, "stories": [
        {"content_id": "quiz-1", "kind": "quiz", "genre": "challenge"}]})
    from astra_v2 import proposal_history
    monkeypatch.setattr(proposal_history, "load_history", lambda *args: ())
    for name in ("stories.json", "reviews.json", "state.json", "history.json"):
        (tmp_path / name).write_text(json.dumps({"stories": [], "reviews": []}))
    for key, name in (("ASTRA_EDITORIAL_STORIES_FILE", "stories.json"), ("ASTRA_EDITORIAL_REVIEWS_FILE", "reviews.json"), ("ASTRA_PUBLISHER_STATE_PATH", "state.json"), ("ASTRA_STORY_HISTORY_PATH", "history.json")):
        monkeypatch.setenv(key, str(tmp_path / name))
    assert load_editorial_stories()[0]["genre"] == "challenge"
