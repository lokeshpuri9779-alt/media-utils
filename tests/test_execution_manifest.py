from execution_manifest import build, verify, worker_accept

def test_canary_is_forced_private():
    m=build("j",{"action":"run_canary","route":"r","private_only":False})
    assert m["payload"]["private_only"] is True

def test_manifest_tampering_is_rejected():
    m=build("j",{"action":"render","route":"r","profile":"p","release":{"requires_quality_gate":True}})
    m["payload"]["route"]="evil"
    assert not verify(m)["valid"]

def test_worker_cannot_disable_quality_gate():
    m=build("j",{"action":"render","route":"r","profile":"p","release":{"requires_quality_gate":True}})
    x=worker_accept(m,{"requires_quality_gate":False})
    assert not x["accepted"]

def test_worker_cannot_switch_route_or_profile():
    m=build("j",{"action":"render","route":"r","profile":"prod","release":{"requires_quality_gate":True}})
    assert not worker_accept(m,{"route":"other"})["accepted"]
    assert not worker_accept(m,{"profile":"cheap"})["accepted"]

def test_exact_manifest_is_accepted():
    m=build("j",{"action":"render","route":"r","profile":"prod","release":{"requires_quality_gate":True}})
    assert worker_accept(m,{"route":"r","profile":"prod"})["accepted"]
