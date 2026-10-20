import json
from astra_v2.story_review_shortlist import shortlist


def test_setup_resolution_subject_switch_is_diagnostic_only(tmp_path):
    stories = [
        {"content_id": "a", "title": "Disconnected", "production_ready": False,
         "story_beats": [{"speech": "The lighthouse stopped working.", "visual": "lighthouse"},
                         {"speech": "The town restored its water.", "visual": "river"}]},
        {"content_id": "b", "title": "Connected", "production_ready": False,
         "story_beats": [{"speech": "The bell stopped working.", "visual": "bell"},
                         {"speech": "The bell rang again.", "visual": "bell"}]},
        {"content_id": "c", "title": "Unclear", "production_ready": False,
         "story_beats": [{"speech": "A strange mystery appeared.", "visual": "forest"},
                         {"speech": "Everyone celebrated.", "visual": "forest"}]},
    ]
    audits = [{"content_id": s["content_id"],
               "editorial_issues": ["human_or_model_editorial_review_required"],
               "publication_rejection": "unreviewed_causal_draft"} for s in stories]
    ledger, review, output = [tmp_path / n for n in ("ledger.json", "review.json", "out.json")]
    ledger.write_text(json.dumps({"proposals": stories}))
    review.write_text(json.dumps({"proposals": audits}))
    result = shortlist(ledger, review, output)
    assert result["candidates_with_resolution_continuity_flags"] == 1
    assert [s["resolution_continuity_flags"] for s in result["review_candidates"]] == [
        ["setup_resolution_subject_switch"], [], []
    ]
    assert result["approved_for_production"] == 0
    assert result["publication_enabled"] is False
