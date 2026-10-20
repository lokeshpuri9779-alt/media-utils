import json
from astra_v2.story_review_shortlist import shortlist


def test_shortlist_skips_repeated_titles_and_keeps_unapproved(tmp_path):
    titles = ["Repeated Story", " repeated story ", "Unique Story"]
    stories = [{"content_id": f"story-{i}", "title": title,
                "production_ready": False, "story_beats": [{"speech": title}]}
               for i, title in enumerate(titles)]
    audits = [{"content_id": story["content_id"],
               "editorial_issues": ["human_or_model_editorial_review_required"],
               "publication_rejection": "unreviewed_causal_draft"}
              for story in stories]
    ledger, review, output = (tmp_path / name for name in
                              ("ledger.json", "review.json", "shortlist.json"))
    ledger.write_text(json.dumps({"proposals": stories}))
    review.write_text(json.dumps({"proposals": audits}))
    result = shortlist(ledger, review, output)
    assert result["candidate_count"] == 2
    assert [item["content_id"] for item in result["review_candidates"]] == ["story-0", "story-2"]
    assert all(item["production_ready"] is False and
               item["eligible_for_automatic_publishing"] is False
               for item in result["review_candidates"])
    assert result["publication_enabled"] is False
