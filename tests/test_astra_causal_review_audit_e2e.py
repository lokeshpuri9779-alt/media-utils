"""End-to-end causal-repeat rejection and journal evidence without external AI."""
import json

from astra_v2.independent_editorial_reviewer import assess
from astra_v2.editorial_review_journal import record_review


def test_repeated_causal_arc_is_rejected_and_audited_without_api(tmp_path):
    arc = {
        "central_conflict": "A village bridge collapses during a storm",
        "decisive_choice": "The engineer reroutes the rescue convoy",
        "resolution": "The stranded families escape along the railway",
    }
    prior = {**arc, "content_id": "prior-published", "title": "Old Bridge Rescue"}
    candidate = {**arc, "content_id": "new-story", "title": "New Rescue Tale",
                 "kind": "authored_causal_story", "production_ready": True,
                 "story_beats": []}
    def forbidden_transport(_request):
        raise AssertionError("duplicate must be rejected before external AI review")
    verdict = assess(candidate, [prior], api_key="not-used", transport=forbidden_transport)
    assert not verdict["approved"]
    assert "repeated_causal_premise" in verdict["issues"]
    assert verdict["record"] is None
    path = tmp_path / "editorial-reviews.json"
    entry = record_review(candidate, verdict, path, [prior])
    assert entry["causal_repeat_evidence"]["matched_content_id"] == "prior-published"
    assert entry["causal_repeat_evidence"]["matched_title"] == "Old Bridge Rescue"
    assert not entry["approved"]
    persisted = json.loads(path.read_text(encoding="utf-8"))["reviews"][0]
    assert persisted["causal_repeat_evidence"] == entry["causal_repeat_evidence"]
