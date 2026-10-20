import json
from astra_v2.story_review_shortlist import shortlist


def test_reused_narration_is_reported_without_approval(tmp_path):
    stories = [
        {"content_id": "a", "title": "Bridge", "production_ready": False,
         "story_beats": [{"speech": "The same clue appeared.", "visual": "river"}]},
        {"content_id": "b", "title": "Tower", "production_ready": False,
         "story_beats": [{"speech": "  THE same clue appeared.  ", "visual": "tower"}]},
        {"content_id": "c", "title": "Forest", "production_ready": False,
         "story_beats": [{"speech": "A different discovery.", "visual": "forest"}]},
    ]
    audits = [{"content_id": x["content_id"],
               "editorial_issues": ["human_or_model_editorial_review_required"],
               "publication_rejection": "unreviewed_causal_draft"}
              for x in stories]
    ledger, review, output = [tmp_path / x for x in ("ledger.json", "review.json", "out.json")]
    ledger.write_text(json.dumps({"proposals": stories}))
    review.write_text(json.dumps({"proposals": audits}))
    result = shortlist(ledger, review, output)
    assert result["candidates_with_reused_narration"] == 2
    assert [x["reused_narration_beats"] for x in result["review_candidates"]] == [1, 1, 0]
    assert result["approved_for_production"] == 0
    assert result["publication_enabled"] is False
    assert all(x["eligible_for_automatic_publishing"] is False for x in result["review_candidates"])
