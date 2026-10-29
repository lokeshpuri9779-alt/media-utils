# SDXL configuration audit after run 40854430774

## Finding

No concrete latent-shape, scaling, scheduler, or size-conditioning mismatch was found in the inspected configuration and version-tagged source. This is a static audit, not a runtime tensor trace or proof of model correctness. The duplicated fire engines remain a failed semantic check.

No generation code, limits, approval settings, or production integration were changed by this audit.

## Evidence

The following files were retrieved at model revision d54e5b43fcb6b4b358f3a134269115d3fcb3eb25. Each SHA-256 matched the manifest archived by run 40854430774:
- unet/config.json
- vae_decoder/config.json
- model_index.json
- scheduler/scheduler_config.json

Sources:
- [Pinned model files](https://huggingface.co/OpenVINO/stable-diffusion-xl-base-1.0-int8-ov/tree/d54e5b43fcb6b4b358f3a134269115d3fcb3eb25)
- [Optimum Intel v2.2.0 diffusion wrapper](https://github.com/huggingface/optimum-intel/blob/v2.2.0/optimum/intel/openvino/modeling_diffusion.py)
- [Diffusers v0.39.0 SDXL pipeline](https://github.com/huggingface/diffusers/blob/v0.39.0/src/diffusers/pipelines/stable_diffusion_xl/pipeline_stable_diffusion_xl.py)
- [Tested benchmark implementation](https://github.com/lokeshpuri9779-alt/media-utils/blob/885973a7584a48ab87b0191e687df7199a4cf987/tools/experimental_sdxl_load.py)

The package versions match worker-result.json. Version-tagged source was inspected; the installed wheel source was not archived or byte-compared.

| Check | Result |
| --- | --- |
| Latent channels and spatial scale | UNet in_channels=4; VAE has four channel blocks, giving spatial factor 8. A 512x512 image requires (1,4,64,64) noise, matching the benchmark. |
| Initial noise scaling | Benchmark passes raw seeded Gaussian noise. Inherited prepare_latents multiplies supplied noise by scheduler.init_noise_sigma once. No benchmark-side double scaling found. |
| Decoder amplitude scaling | VAE scaling_factor=0.13025 is present. Diffusers divides latents by that value before decode; the OpenVINO decoder forwards the tensor without a second division. |
| Scheduler | Model index selects EulerDiscreteScheduler. Every field in the pinned scheduler config matches the archived runtime config. Additional runtime defaults do not replace the pinned values. |
| SDXL size conditioning | Omitted original_size and target_size resolve to requested height/width, both (512,512); crop defaults to (0,0). Expected time IDs are [512,512,0,0,512,512]. Negative conditioning reuses these IDs when negative sizes are absent. These values are source-derived, not directly captured from the completed run. |
| Guidance batch | OpenVINO doubles the internal UNet batch for classifier-free guidance. That is not two output images; the artifact contains one PNG with two depicted objects. |
| Model default resolution | UNet sample_size=128 times VAE factor 8 gives 1024. VAE sample_size also says 1024. Explicit 512 dimensions override the pipeline default; the reshape follows the explicit size. |

## Interpretation

512x512 is below this model's default output resolution. That is a quality limitation worth testing, not evidence of an implementation bug or proof that resolution caused duplication. Matching configuration does not validate the compressed weights, graph conversion, text encoders, or semantic fidelity.

The UNet and VAE configs contain a source snapshot path ending in 462165984030d82259a11f4367a4eed129e94a7b. This is a provenance clue, not verified exact original-weight parity; no FP32 parity claim is made.

## Smallest next image validation

Stop prompt and seed sweeps. A useful next bounded control is one 1024x1024, 20-step image using the current single-vehicle prompt, same model revision, scheduler, guidance and seed, with explicit size conditioning and recorded resolved configuration. The previous 1024 attempt timed out at 600 seconds without a PNG, so repeating that unchanged budget is unlikely to resolve visual quality. A proposed 900-second inference allowance would be a separate diagnostic budget change, not a production fallback; it has not been implemented or dispatched by this audit.

Keep the 12 GiB RSS cap and 2 GiB available-memory floor. Account for dependency installation separately within the workflow time budget before launching. Save initial latents and size IDs; the larger latent shape means that seed 42 does not make the noise byte-identical to the 512 control. Judge object count, coherence, ladder, framing and background manually. Stop if it fails or times out; do not start an unbounded resolution sweep.

Even a passing single image would only justify a small scene/identity validation afterward. It would not establish reliable ASTRA story generation.

approved=false; production_ready=false; published=false; manual_visual_review_required=true. Automatic approval, production fallback, paid APIs and publishing remain outside this experiment.
