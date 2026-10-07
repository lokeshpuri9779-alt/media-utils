from self_migration import decide, next_canary_history

GOOD={"key":"new","health_ok":True,"render_feasible":True,"quality_passed":True,"ready":True,"score":90}
BAD={"key":"old","health_ok":False,"render_feasible":False,"quality_passed":False,"ready":False}

def test_keeps_healthy_current_route():
    cur=dict(GOOD,key="old")
    assert decide(cur,[GOOD],{"new":2})["action"]=="keep"

def test_does_not_promote_after_one_canary():
    x=decide(BAD,[GOOD],{"new":1})
    assert x["action"]=="canary"

def test_migrates_after_repeated_canary_passes():
    x=decide(BAD,[GOOD],{"new":2})
    assert x["action"]=="migrate" and x["selected"]=="new"

def test_no_safe_replacement_checkpoints():
    x=decide(BAD,[],{})
    assert x["action"]=="checkpoint" and x["selected"] is None

def test_failed_canary_resets_streak():
    assert next_canary_history({"new":1},"new",False)["new"]==0
