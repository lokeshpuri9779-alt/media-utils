import json
from astra_v2.story_review_shortlist import shortlist


def test_visual_cue_mismatch_is_review_only(tmp_path):
    stories = [
        {"content_id": "a", "title": "Bell Repair", "production_ready": False,
         "story_beats": [{"speech": "The bell stopped ringing.", "visual": "river"}]},
        {"content_id": "b", "title": "Bell Restored", "production_ready": False,
         "story_beats": [{"speech": "The bell rang again.", "visual": "bell"}]},
        {"content_id": "c", "title": "Uncertain", "production_ready": False,
         "story_beats": [{"speech": "The bell and bridge were damaged.", "visual": "snow"}]},
    ]
    audits = [{"content_id": s["content_id"],
               "editorial_issues": ["human_or_model_editorial_review_required"],
               "publication_rejection": "unreviewed_causal_draft"} for s in stories]
    ledger, review, output = [tmp_path / n for n in ("ledger.json", "review.json", "out.json")]
    ledger.write_text(json.dumps({"proposals": stories}))
    review.write_text(json.dumps({"proposals": audits}))
    result = shortlist(ledger, review, output)
    assert result["candidates_with_visual_alignment_flags"] == 1
    assert [s["visual_alignment_flags"] for s in result["review_candidates"]] == [
        ["scene_1_visual_cue_mismatch"], [], []
    ]
    assert result["approved_for_production"] == 0
    assert result["publication_enabled"] is False
