import json
from runtime_state import default_state, load, save, quarantine, record_canary, checkpoint

def test_state_survives_restart(tmp_path):
    p=tmp_path/"state.json"
    s=record_canary(default_state(),"renderer-a",True)
    s["active_route"]="renderer-a"
    save(p,s)
    r=load(p)
    assert r["active_route"]=="renderer-a"
    assert r["canary_passes"]["renderer-a"]==1

def test_corrupt_state_fails_closed(tmp_path):
    p=tmp_path/"state.json"; p.write_text("{broken")
    r=load(p)
    assert r["active_route"] is None
    assert r["recovery"]=="corrupt_state_fail_closed"

def test_quarantine_removes_active_route():
    s=default_state(); s["active_route"]="bad"
    r=quarantine(s,"bad","oom")
    assert r["active_route"] is None and r["quarantined"]["bad"]["reason"]=="oom"

def test_failed_canary_resets_streak():
    s=record_canary(default_state(),"x",True)
    assert record_canary(s,"x",False)["canary_passes"]["x"]==0

def test_checkpoint_is_persistable(tmp_path):
    p=tmp_path/"state.json"
    save(p,checkpoint(default_state(),"job-1",{"stage":"render","attempt":2}))
    assert load(p)["checkpoints"]["job-1"]["attempt"]==2
