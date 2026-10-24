from astra_v2.story_editorial import editorial_issues


def test_same_causal_arc_is_an_editorial_blocker():
    arc = {"central_conflict": "A town bridge collapses in a storm",
           "decisive_choice": "The engineer diverts the rescue convoy",
           "resolution": "The trapped villagers escape along the railway"}
    story = {**arc, "kind": "authored_causal_story", "story_beats": []}
    assert "repeated_causal_premise" in editorial_issues(story, [{**arc, "content_id": "old"}])


def test_missing_or_distinct_arc_is_not_a_causal_blocker():
    arc = {"central_conflict": "A town bridge collapses in a storm",
           "decisive_choice": "The engineer diverts the rescue convoy",
           "resolution": "The trapped villagers escape along the railway"}
    story = {**arc, "story_beats": []}
    changed = {**arc, "resolution": "A helicopter rescues everyone from the rooftops"}
    assert "repeated_causal_premise" not in editorial_issues(story, [changed])
    assert "repeated_causal_premise" not in editorial_issues(story, [{"content_id": "old"}])
