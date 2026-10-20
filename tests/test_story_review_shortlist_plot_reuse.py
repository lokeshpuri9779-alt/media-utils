import json
from astra_v2.story_review_shortlist import shortlist


def test_repeated_plot_arc_detected_despite_different_opening(tmp_path):
    common = [
        {"speech": "The hero found a hidden second control.", "visual": "book"},
        {"speech": "The hero repaired the broken bell.", "visual": "bell"},
    ]
    stories = [
        {"content_id": "a", "title": "Forest", "production_ready": False,
         "story_beats": [{"speech": "A fox entered the forest."}, *common]},
        {"content_id": "b", "title": "Museum", "production_ready": False,
         "story_beats": [{"speech": "A robot entered the museum."}, *common]},
        {"content_id": "c", "title": "Bridge", "production_ready": False,
         "story_beats": [{"speech": "A child crossed the bridge."},
                         {"speech": "The child found a map."},
                         {"speech": "The child returned home."}]},
    ]
    audits = [{"content_id": s["content_id"],
               "editorial_issues": ["human_or_model_editorial_review_required"],
               "publication_rejection": "unreviewed_causal_draft"} for s in stories]
    ledger, review, output = [tmp_path / n for n in ("ledger.json", "review.json", "out.json")]
    ledger.write_text(json.dumps({"proposals": stories}))
    review.write_text(json.dumps({"proposals": audits}))
    result = shortlist(ledger, review, output)
    assert result["candidates_with_reused_plot_arc"] == 2
    assert [s["reused_plot_arc"] for s in result["review_candidates"]] == [True, True, False]
    assert result["approved_for_production"] == 0
    assert result["publication_enabled"] is False
