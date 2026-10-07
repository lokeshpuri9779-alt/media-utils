from omniroute_video import policy
def test_no_local_gpu():
    assert policy()["local_gpu_required"] is False
def test_no_paid_fallback():
    assert policy()["paid_fallback"] is False
def test_private_quality_gate():
    p=policy()
    assert p["private_canary"] and p["quality_gate_required"]
