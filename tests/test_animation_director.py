from animation_director import direction, continuity_state

def test_short_and_long_share_quality_core_but_differ_in_pacing():
    short=direction("short")
    long=direction("long")
    assert "coherent sequences rather than unrelated generated clips" in short["principles"]
    assert "coherent sequences rather than unrelated generated clips" in long["principles"]
    assert "enter action immediately" in short["principles"]
    assert "allow emotional holds when story requires" in long["principles"]

def test_no_fixed_clip_count_architecture():
    joined=" ".join(direction("short")["principles"]+direction("long")["principles"]).lower()
    assert "20" not in joined and "22" not in joined and "25" not in joined
    assert "never a fixed clip quota" in joined

def test_stitched_clip_feel_is_hard_failure():
    assert "stitched_clip_feel" in direction("long")["hard_failures"]

def test_continuity_state_persists_and_updates():
    a=continuity_state(characters={"hero":"same"}, location="village", props={"ball":"left hand"})
    b=continuity_state(a, location="forest", goals_emotions={"hero":"worried"})
    assert b["characters"]=={"hero":"same"}
    assert b["props"]=={"ball":"left hand"}
    assert b["location"]=="forest"
