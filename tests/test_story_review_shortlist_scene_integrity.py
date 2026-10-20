import json
from astra_v2.story_review_shortlist import shortlist


def test_scene_integrity_flags_are_diagnostic_only(tmp_path):
    stories = [
        {"content_id": "a", "title": "Broken Sequence", "production_ready": False,
         "story_beats": [
             {"story_beat": "build", "speech": "A clue appeared.", "visual": "book"},
             {"story_beat": "reveal", "speech": " ", "visual": ""},
             {"story_beat": "payoff", "speech": "The bell rang.", "visual": "bell"}]},
        {"content_id": "b", "title": "Complete Sequence", "production_ready": False,
         "story_beats": [
             {"story_beat": "reveal", "speech": "A clue appeared.", "visual": "book"},
             {"story_beat": "build", "speech": "The search continued.", "visual": "path"},
             {"story_beat": "twist", "speech": "A new fact emerged.", "visual": "door"},
             {"story_beat": "payoff", "speech": "The bell rang.", "visual": "bell"}]},
    ]
    audits = [{"content_id": s["content_id"],
               "editorial_issues": ["human_or_model_editorial_review_required"],
               "publication_rejection": "unreviewed_causal_draft"} for s in stories]
    ledger, review, output = [tmp_path / n for n in ("ledger.json", "review.json", "out.json")]
    ledger.write_text(json.dumps({"proposals": stories}))
    review.write_text(json.dumps({"proposals": audits}))
    result = shortlist(ledger, review, output)
    assert result["candidates_with_scene_integrity_flags"] == 1
    assert result["review_candidates"][0]["scene_integrity_flags"] == [
        "scene_2_missing_narration", "scene_2_missing_visual", "scene_2_beat_order"
    ]
    assert result["review_candidates"][1]["scene_integrity_flags"] == []
    assert result["approved_for_production"] == 0
    assert result["publication_enabled"] is False
