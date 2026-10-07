from hardware_render_planner import RenderProfile, choose, release_policy

def test_selects_highest_quality_feasible_profile():
    p=[RenderProfile("prod",720,1280,81,30,18,"production"),
       RenderProfile("canary",480,720,49,20,8,"canary")]
    x=choose(p,11)
    assert x["selected"]["name"]=="canary"

def test_blocks_when_nothing_fits():
    p=[RenderProfile("x",720,1280,81,30,20,"production")]
    assert choose(p,10)["status"]=="blocked"

def test_canary_cannot_silently_publish():
    p=RenderProfile("canary",480,720,49,20,8,"canary")
    x=release_policy(p)
    assert x["private_only"] and not x["may_publish"]
