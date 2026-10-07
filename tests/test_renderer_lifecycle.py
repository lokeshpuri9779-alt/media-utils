from renderer_lifecycle import RendererContract, blockers, quality_pass, lifecycle_after_probe, migration_policy

GOOD={"identity":90,"motion":88,"continuity":91,"visual":90,"audio_alignment":88,"technical":95}

def test_new_renderer_cannot_publish_by_discovery_alone():
    r=RendererContract("future_model","1",True,True,True,True,8,True)
    b=blockers(r,{"image_reference":True},15)
    assert "renderer_not_promoted" in b
    assert "renderer_not_approved" in b

def test_canary_needs_two_good_probes_to_become_active():
    assert lifecycle_after_probe("discovered",True,GOOD)=="canary"
    assert lifecycle_after_probe("canary",True,GOOD)=="active"

def test_quality_regression_degrades_active_renderer():
    bad=dict(GOOD,motion=20)
    assert quality_pass(bad)["passed"] is False
    assert lifecycle_after_probe("active",True,bad)=="degraded"

def test_health_failure_quarantines_renderer():
    assert lifecycle_after_probe("active",False,GOOD)=="quarantined"

def test_retired_renderer_never_auto_returns():
    assert lifecycle_after_probe("retired",True,GOOD)=="retired"

def test_paid_spend_remains_explicit():
    assert migration_policy()["paid_spend"]=="explicit_user_approval_required"
