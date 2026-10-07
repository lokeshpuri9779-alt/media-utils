from compute_router import ComputeSurface, select, observed_colab_t4

def test_free_viable_surface_wins_over_paid_without_approval():
    s=[ComputeSurface("free",True,True,24,22,True,0,True),
       ComputeSurface("paid",True,True,80,75,True,2.5,True)]
    assert select(s,16)["selected"]=="free"

def test_paid_is_blocked_without_explicit_approval():
    s=[ComputeSurface("paid",True,True,80,75,True,2.5,True)]
    x=select(s,16)
    assert x["selected"] is None
    assert "paid_compute_disabled" in x["ranked"][0]["blockers"]

def test_no_free_capacity_checkpoints_instead_of_fake_fallback():
    s=[ComputeSurface("free",False,True,24,0,True,0,True)]
    assert select(s,16)["status"]=="checkpointed_waiting_for_capacity"

def test_observed_t4_does_not_meet_16gb_requirement():
    assert select([observed_colab_t4()],16)["selected"] is None

def test_unattended_requirement_is_real_blocker():
    x=select([observed_colab_t4()],8,require_unattended=True)
    assert x["selected"] is None
    assert "unattended_execution_not_supported" in x["ranked"][0]["blockers"]
