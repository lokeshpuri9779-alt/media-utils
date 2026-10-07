from durable_orchestrator import plan_job, finish_canary, finish_render
from runtime_state import default_state
from render_preflight import RenderProbe
from hardware_render_planner import RenderProfile

GOOD={"key":"route-new","health_ok":True,"render_feasible":True,"quality_passed":True,"ready":True,"score":90}
BAD={"key":"route-old","health_ok":False,"render_feasible":False,"quality_passed":False,"ready":False}
PROFILE=RenderProfile("production",720,1280,49,30,8,"production")
PROBE=RenderProbe("renderer",24,20,estimated_peak_gb=8,model_loaded=True)

def test_failed_current_route_runs_private_canary_before_migration():
    x=plan_job({"id":"j1"},default_state(),BAD,[GOOD],None,None)
    assert x["action"]=="run_canary" and x["private_only"]

def test_two_canaries_allow_migration_and_render():
    s=default_state(); s["canary_passes"]={"route-new":2}
    x=plan_job({"id":"j1"},s,BAD,[GOOD],PROBE,PROFILE)
    assert x["action"]=="render" and x["route"]=="route-new"
    assert x["release"]["requires_quality_gate"]

def test_preflight_failure_quarantines_and_checkpoints():
    s=default_state(); s["canary_passes"]={"route-new":2}
    badprobe=RenderProbe("renderer",14.56,11,observed_oom_request_gb=113.01,model_loaded=True)
    x=plan_job({"id":"j1"},s,BAD,[GOOD],badprobe,PROFILE)
    assert x["action"]=="checkpoint"
    assert "route-new" in x["state"]["quarantined"]

def test_no_route_checkpoints():
    x=plan_job({"id":"j1"},default_state(),BAD,[],None,None)
    assert x["action"]=="checkpoint" and x["stage"]=="route_selection"

def test_failed_quality_keeps_job_checkpoint():
    s=finish_render(default_state(),"j1",False)
    assert s["checkpoints"]["j1"]["stage"]=="quality_gate"
