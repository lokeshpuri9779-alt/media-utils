from hunyuan_i2v_pilot import build_job

def test_pilot_is_private_reference_conditioned_and_free_fail_closed():
    j=build_job("hero.png","A small original animated character runs through a garden.")
    assert j["private_pilot"] is True
    assert j["minimum_vram_gb"]==14
    assert j["mode"]=="i2v"
    assert "--image_path hero.png" in j["command"]
    assert "--enable_step_distill true" in j["command"]
    assert "--rewrite false" in j["command"]
    assert "reference-animation-v1"==j["animation_profile"]
