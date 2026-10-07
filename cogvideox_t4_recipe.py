"""CogVideoX T4 canary worker recipe.

This is an execution recipe, not a production promotion. It encodes the official
low-memory strategy: INT8 quantization plus sequential CPU offload and VAE tiling.
"""
RECIPE={
 "model":"THUDM/CogVideoX-5b-I2V",
 "hardware":"nvidia_t4_16gb",
 "quantization":{
   "backend":"torchao",
   "transformer":"int8_weight_only",
 },
 "offload":"sequential_cpu_offload",
 "vae_slicing":True,
 "vae_tiling":True,
 "private_only":True,
 "production_publish":False,
 "quality_gate_required":True,
 "notes":[
   "Do not call pipeline.to('cuda') before sequential CPU offload.",
   "Treat successful render as canary evidence only.",
   "Do not reuse quarantined BF16 T4 configuration."
 ]
}

def validate_recipe(r=RECIPE):
    failures=[]
    if r["hardware"]!="nvidia_t4_16gb": failures.append("wrong_hardware_profile")
    if r["quantization"]["transformer"]!="int8_weight_only": failures.append("t4_requires_quantized_canary")
    if r["offload"]!="sequential_cpu_offload": failures.append("low_memory_offload_required")
    if not r["vae_tiling"]: failures.append("vae_tiling_required")
    if not r["private_only"] or r["production_publish"]: failures.append("canary_release_violation")
    return {"valid":not failures,"failures":failures}
