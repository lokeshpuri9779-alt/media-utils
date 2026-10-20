"""Protect approved beat-sheet rendering without legacy question/answer."""
import pytest
from studio_renderer import _story_plan


def test_reviewed_story_renders_four_beats_without_legacy_fields():
    story = {"genre": "fiction", "content_id": "approved-bell", "story_beats": [
        {"story_beat": role, "speech": f"Narration for {role}.", "visual": "railway_bridge"}
        for role in ("reveal", "build", "twist", "payoff")]}
    plan = _story_plan(story)
    assert len(plan) == 4
    assert [shot["headline"] for shot in plan] == ["REVEAL", "BUILD", "TWIST", "PAYOFF"]
    assert all(shot["speech"] and shot["visual"] for shot in plan)


def test_existing_authored_headline_preserved():
    story = {"story_beats": [{"headline": "THE SIGNAL", "speech": "A bell rang.", "visual": "signal_bell"}]}
    assert _story_plan(story)[0]["headline"] == "THE SIGNAL"


def test_empty_authored_beat_fails_closed():
    with pytest.raises(ValueError, match="requires speech and visual"):
        _story_plan({"story_beats": [{"story_beat": "reveal", "speech": "", "visual": "signal_bell"}]})
