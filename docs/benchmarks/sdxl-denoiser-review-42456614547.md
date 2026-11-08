# FP32 source-denoiser first-step comparison

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/42456614547 (#81)
Code: caa7889e5b7b9639610eb2a9317fa5f26825f4d3
Artifact: astra-sdxl-denoiser-review-42456614547 (13607484787)

## Outcome

The isolated FP32 source denoiser completed both first-step conditioning rows on the free CPU runner within the existing resource limits. This establishes feasibility for this bounded diagnostic, not a reliable image path or a semantic pass. No images were generated and no scheduler updates were performed.

The measured difference from the archived INT8 OpenVINO prediction is:

| Quantity | Relative L2 difference, using FP32 as denominator | Cosine similarity |
| --- | ---: | ---: |
| Negative prediction | 0.433854% | 0.9999906014 |
| Positive prediction | 0.434960% | 0.9999905501 |
| Positive minus negative (prompt residual) | 2.665308% | 0.9997098793 |
| Classifier-free guided prediction | 0.495467% | 0.9999877293 |
| Implied clean latent at step zero | 5.009579% | 0.9989622943 |

The implied clean latent is calculated as initial_latent - sigma * guided_prediction; it is not a decoded image or a scheduler advance. Large common noise components can make prediction cosine similarity look close to one while masking larger relative differences in the prompt residual or implied clean latent. None of these metrics has an automatic semantic acceptance threshold.

## Controls and limits

- Same saved seed-42 initial latent from run 42232753910, timestep 951, scaled sample and source FP32 text-conditioning pack from run 42192924660.
- Same 20-step Euler schedule, sigma 11.028335571289062, guidance 7.5, 1024-square request and negative/positive row ordering.
- Reference: stabilityai/stable-diffusion-xl-base-1.0 at 462165984030d82259a11f4367a4eed129e94a7b; original FP32 U-Net weights.
- Candidate: archived INT8 OpenVINO U-Net output from run 42232753910 using identical reference text conditioning. No new INT8 inference was needed.
- PyTorch reference rows ran sequentially at batch size one, with maximum attention slicing, two CPU threads and no precision conversion. Source configuration matched the pinned export configuration.
- Model initialized on the meta device, followed by strict assignment of safetensors-backed CPU weights. No text encoder or decoder was loaded.
- RAM/disk screening ran before weight download. It required weights plus measured runtime RSS and a 1 GiB workspace allowance, with the separate 2 GiB available-RAM floor. This was a screening estimate, not a guarantee; the existing supervisor remained active.
- Unchanged caps: 12 GiB sampled process-tree RSS, 2 GiB minimum available RAM, 600 seconds load, 900 seconds predictions and 1200 seconds total.

Observed:
- Worker duration: 119.103997722 seconds; exit code 0.
- Negative/positive forward times: 35.172064448 / 34.383307216 seconds.
- Peak sampled process-tree RSS: 11,268,698,112 bytes (10.494793 GiB).
- Runner: AMD EPYC 9V45, four available logical CPUs, two PyTorch threads.
- Weight file: 10,270,077,736 bytes; model parameter storage: 10,269,854,736 bytes.
- Runtime: torch 2.14.1+cpu, diffusers 0.39.0, safetensors 0.8.0, numpy 2.4.6, psutil 7.0.0.
- All 42 offline tests passed locally and on the runner.

## Independent verification

Downloaded ZIP digest, all five output-file hashes, concatenation/order of separate prediction rows, scaled-sample hash and all five metric groups were independently checked. Every archived JSON retained zero images, zero scheduler updates and review-only flags.

SHA-256:
- ZIP: ef45b09cdaceffb3b73c3289581ca38a7ff2b6b280ec63431b30c0cb7a1cb947
- FP32 combined prediction: 680a029b59f316947d38d5df026f3d07790bb24be0ab424c2b403ed9fe178c7c
- INT8 prediction: 59e67dc59c95f9d4ae20bf17619ce0dcd9c87d304d1da1fa5f66d5fa9b94b5c2
- Scaled sample raw bytes: feaff25c7684b1281f1cba182d9c71494c2f14762b8341ee3ec9daecd9466419
- Reference weight file: 357650fbfb3c7b4d94c1f5fd7664da819ad1ff5a839430484b4ec422d03f710a

Source weight metadata:
https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/462165984030d82259a11f4367a4eed129e94a7b/unet/diffusion_pytorch_model.safetensors

## Interpretation and next validation

This comparison identifies a measurable denoiser-path difference. It does not establish quantization as the cause of the collage failure: backend, arithmetic ordering, attention implementation and batch execution differ too. It tests only timestep zero. Different runner hardware also prevents treating these timings as a controlled speed comparison against earlier OpenVINO runs.

The smallest useful next visual test is one matched 20-step seed-42 image using the source FP32 denoiser throughout, retaining the same reference text inputs, scheduler, prompt and original decoder. Reuse the verified FP32 first prediction, run the remaining 19 steps as separate negative/positive rows, checkpoint final latents, then release the denoiser before loading the decoder. Keep the existing slow-review resource/time limits and stop on any breach. Judge the resulting image against the same exact-one-centered-fire-engine rubric and run-80 baseline.

A successful image would still be a single manually reviewed case. Repeated prompt fidelity, recognizable school scenes and cross-scene character consistency would remain separate validation requirements. No such quality claim is established here.

approved=false
production_ready=false
published=false
manual_visual_review_required=true

No automatic approval, production fallback, paid API, merge, or content publishing was enabled.
