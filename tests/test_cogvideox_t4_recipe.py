from cogvideox_t4_recipe import RECIPE, validate_recipe
def test_t4_recipe_is_quantized_and_private():
    assert validate_recipe()["valid"]
    assert RECIPE["quantization"]["transformer"]=="int8_weight_only"
    assert RECIPE["private_only"] and not RECIPE["production_publish"]
def test_cuda_preload_is_explicitly_forbidden():
    assert any("pipeline.to('cuda')" in x for x in RECIPE["notes"])
