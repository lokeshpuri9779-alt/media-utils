# One reference VAE decode of the run-76 checkpoint

Run 41988573278 produced a native 1024x1024 PNG but failed the requested
single-truck composition: many trucks and fragments fill the canvas. This
follow-up holds its final latent fixed and compares the exported decoder's
output with the original FP32 VAE on CPU. No new denoising is requested.

## Provenance verified before implementation

The pinned OpenVINO VAE config identifies this source snapshot in its
recorded model path:

- Source: stabilityai/stable-diffusion-xl-base-1.0
- Revision: 462165984030d82259a11f4367a4eed129e94a7b
- Subfolder: vae
- Reference FP32 weights: vae/diffusion_pytorch_model.safetensors
- Weight bytes: 334643268
- Weight SHA-256: 1598f3d24932bcfe6634e8b618ea1e30ab1d57f5aad13a6d2de446d2199f2341
- Reference config SHA-256: 0b331c8ac22ded5f9997a144a575c1d113d6169aff262c353f39015bd24a6264
- Exported config SHA-256: d93c03a11ecbd4ecb37c9091e99575ca1b4c8c6302f027024c5570c58cd1f793

Both configs agree on AutoencoderKL architecture, four latent channels,
1024 sample size and 0.13025 scaling. The newer export explicitly includes
defaults for mean/std, shift, attention and quant/post-quant convolution;
these match the pinned Diffusers implementation's defaults. The reference
is the recorded source model, not bit-identical INT8 weights. The comparison
therefore tests the combined effect of exported/quantized decoding versus
FP32 reference decoding; it cannot isolate quantization from backend effects.

Primary sources:

- https://huggingface.co/OpenVINO/stable-diffusion-xl-base-1.0-int8-ov/blob/d54e5b43fcb6b4b358f3a134269115d3fcb3eb25/vae_decoder/config.json
- https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/462165984030d82259a11f4367a4eed129e94a7b/vae/config.json
- https://huggingface.co/api/models/stabilityai/stable-diffusion-xl-base-1.0/revision/462165984030d82259a11f4367a4eed129e94a7b?blobs=true
- https://github.com/huggingface/diffusers/blob/v0.39.0/src/diffusers/models/autoencoders/autoencoder_kl.py
- https://github.com/huggingface/diffusers/blob/v0.39.0/src/diffusers/pipelines/stable_diffusion_xl/pipeline_stable_diffusion_xl.py

## Bounded manual execution

The existing manual workflow accepts BENCHMARK_DECODE_REVIEW with every
diagnostic checkbox off. No input, schedule, production route or approval
mechanism is added. Its dedicated job has contents:read and actions:read
permissions, needed only to retrieve the fixed run-76 artifact.

The runner retrieves astra-sdxl-one-image-41988573278 and checks six pinned
source hashes before any model download. The latent is loaded without pickle
and must be finite float32 with shape (1,4,128,128), the recorded model/revision,
20 completed steps and raw_scheduler_output_unscaled metadata. Source image,
request, conditioning and report hashes prevent substituting another attempt.

Only two configs and the 334.6 MB reference VAE weights are downloaded, each
with exact byte and SHA-256 checks. No text encoder, tokenizer, UNet or full
pipeline is loaded. The CPU FP32 AutoencoderKL must load without missing,
unexpected or mismatched weights. Tiling and slicing are disabled. The saved
latent is divided by 0.13025 exactly once before one decode call, followed by
the standard VaeImageProcessor. No denoising, prompt, seed or retry is involved.

Memory remains capped at 12 GiB sampled process-tree RSS with a 2 GiB available
RAM floor. Loading is limited to 600 seconds, decoding to 900 seconds and the
worker to 1200 seconds overall. The job has a 40-minute outer timeout including
dependency installation and artifact handling. Failed integrity, resource or
decode checks stop the experiment; there is no alternate provider or fallback.

Outputs include baseline-openvino.png, reference-vae.png, source-latents.npy,
config/provenance hashes, runtime, timing, memory and numeric pixel differences.
Pixel differences carry no automatic semantic verdict. All review outputs keep
approved=false, production_ready=false, published=false, semantic and character
checks not_verified, and manual_visual_review_required=true.

## Validation and interpretation

All 29 offline SDXL tests passed before dispatch, including eight new tests for
source integrity, invalid latent rejection, exactly-once scaling, preserved
input, decode error propagation without retry, reference configuration checks,
failed download integrity, immutable review flags, stale-output refusal and
supervisor deadline enforcement. The real archived checkpoint/configs were
also verified locally, and the workflow parsed with ten inputs and only a
manual trigger. Reference decode execution is pending at this commit.

Inspect the two images directly after completion. A similar many-truck layout
would show that changing the decoder alone does not fix the semantic failure
and would direct the next investigation upstream. A substantially different
layout warrants decoder/configuration analysis before assigning a cause.
Neither outcome establishes cross-scene identity or production reliability.
No automatic approval, production fallback, paid API, content publishing,
merge or main integration is enabled.
