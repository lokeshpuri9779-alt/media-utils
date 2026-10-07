from renderer_profiles import eligible
def test_failed_bf16_profile_stays_quarantined():
    assert not eligible("cogvideox_5b_i2v:t4_bf16_failed",14.5)["eligible"]
def test_int8_canary_is_candidate_on_full_t4():
    assert eligible("cogvideox_5b_i2v:t4_int8_canary",14.5)["eligible"]
def test_int8_canary_is_never_public():
    p=eligible("cogvideox_5b_i2v:t4_int8_canary",14.5)["profile"]
    assert p["private_only"] and not p["publish_allowed"]
