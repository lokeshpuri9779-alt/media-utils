from render_preflight import RenderProbe, assess, cogvideox_t4_failed_canary

def test_model_load_does_not_imply_render_feasible():
    x=cogvideox_t4_failed_canary()
    assert x["probe"]["model_loaded"] is True
    assert x["render_feasible"] is False
    assert x["action"]=="reject_before_inference"
    assert "observed_allocation_exceeds_safe_vram" in x["reasons"]

def test_estimated_peak_is_checked_before_render():
    x=assess(RenderProbe("future",16,14,estimated_peak_gb=20,model_loaded=True))
    assert not x["render_feasible"]

def test_feasible_probe_can_render():
    x=assess(RenderProbe("future",24,22,estimated_peak_gb=12,model_loaded=True))
    assert x["render_feasible"]
    assert x["action"]=="render"
