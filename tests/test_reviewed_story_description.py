"""Regression coverage for reviewed story description compatibility."""
from astra_v2.creative import story_description_text


def test_reviewed_story_uses_authored_beats():
    story = {"kind": "authored_causal_story", "story_beats": [
        {"speech": "The crossing flooded."}, {"speech": "Otter raised the lantern."}]}
    assert story_description_text(story) == "The crossing flooded.\nOtter raised the lantern."


def test_legacy_question_answer_preserved():
    assert story_description_text({"question": "Why?", "answer": "Because."}) == "Why?\nBecause."


def test_empty_reviewed_story_fails_closed():
    import pytest
    with pytest.raises(ValueError, match="no description narration"):
        story_description_text({"story_beats": []})
