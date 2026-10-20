import json
from astra_v2.story_review_shortlist import shortlist


def test_shortlist_includes_reviewable_beats_without_approval(tmp_path):
    story = {
        "content_id": "story-1", "title": "A Bridge", "genre": "fiction",
        "production_ready": False,
        "story_beats": [
            {"story_beat": "reveal", "headline": "THE CRISIS",
             "speech": "The bridge was closed.", "visual": "river"},
            {"story_beat": "payoff", "headline": "THE RESULT",
             "speech": "The repair passed inspection.", "visual": "bridge"},
        ],
    }
    audit = {"content_id": "story-1",
             "editorial_issues": ["human_or_model_editorial_review_required"],
             "publication_rejection": "unreviewed_causal_draft"}
    ledger = tmp_path / "ledger.json"
    review = tmp_path / "review.json"
    output = tmp_path / "shortlist.json"
    ledger.write_text(json.dumps({"proposals": [story]}), encoding="utf-8")
    review.write_text(json.dumps({"proposals": [audit]}), encoding="utf-8")
    result = shortlist(ledger, review, output)
    entry = result["review_candidates"][0]
    assert entry["story_beats"][0]["speech"] == "The bridge was closed."
    assert entry["story_beats"][1]["visual"] == "bridge"
    assert entry["production_ready"] is False
    assert entry["eligible_for_automatic_publishing"] is False
    assert result["publication_enabled"] is False
    assert json.loads(output.read_text()) == result


def test_shortlist_limits_preview_beats(tmp_path):
    story = {"content_id": "story-1", "title": "A Bridge", "genre": "fiction",
             "production_ready": False,
             "story_beats": [{"speech": str(i)} for i in range(20)]}
    ledger = tmp_path / "ledger.json"
    review = tmp_path / "review.json"
    ledger.write_text(json.dumps({"proposals": [story]}))
    review.write_text(json.dumps({"proposals": [{
        "content_id": "story-1",
        "editorial_issues": ["human_or_model_editorial_review_required"],
        "publication_rejection": "unreviewed_causal_draft"}]}))
    result = shortlist(ledger, review, tmp_path / "out.json")
    assert len(result["review_candidates"][0]["story_beats"]) == 12
