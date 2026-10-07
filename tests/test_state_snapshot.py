from runtime_state import default_state
from state_snapshot import export_snapshot, import_snapshot, restore_priority

def test_snapshot_round_trip():
    s=default_state(); s["active_route"]="route-a"; s["canary_passes"]={"route-a":2}
    assert import_snapshot(export_snapshot(s))["active_route"]=="route-a"

def test_tampering_fails_closed():
    snap=export_snapshot(default_state())
    snap["payload"]["state"]["active_route"]="evil"
    r=import_snapshot(snap)
    assert r["active_route"] is None
    assert r["recovery"]=="snapshot_integrity_failure_fail_closed"

def test_remote_restores_ephemeral_runner():
    s=default_state(); s["active_route"]="trusted"
    r=restore_priority(None,export_snapshot(s))
    assert r["active_route"]=="trusted"

def test_valid_local_active_state_wins():
    local=default_state(); local["active_route"]="local"
    remote=default_state(); remote["active_route"]="remote"
    assert restore_priority(local,export_snapshot(remote))["active_route"]=="local"
