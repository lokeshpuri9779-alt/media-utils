from astra_v2.genre_story_supply import SCENARIOS, genre_proposal


def test_genre_proposals_keep_premise_and_cause_through_resolution():
    for scenario_index, (_, _, _, problem, reveal, solution, _) in enumerate(SCENARIOS):
        story = genre_proposal(scenario_index, scenario_index=scenario_index)
        beats = story["story_beats"]
        assert problem in beats[0]["speech"]
        assert problem in beats[1]["speech"]
        assert reveal in beats[2]["speech"]
        assert reveal in beats[3]["speech"]
        assert solution in beats[3]["speech"]
        assert problem in beats[3]["speech"]
        assert story["production_ready"] is False
        assert story["kind"] == "unreviewed_causal_draft"
