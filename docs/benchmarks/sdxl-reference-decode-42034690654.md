# Reference VAE result: the many-truck layout persists

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/42034690654
Run number: 77
Tested commit: 04ee69d767fe5fa5d7f941002e14b5185cb73a2d
Job: 127269665848
Artifact: 13417562459 (astra-sdxl-decode-review-42034690654)
Artifact expires: 2026-11-12T13:21:12Z.
Review date: 2026-11-05.

## Finding

The original FP32 SDXL VAE decoded the saved run-76 latent into essentially the
same collage of red fire trucks and fragments as the OpenVINO INT8 decoder.
Direct inspection of reference-vae.png still fails the requested exactly-one,
centered, fully visible side-view truck composition. Changing the decoder alone
did not correct the semantic failure.

This narrows the investigation upstream of decoding. The repeated layout is
preserved by the original reference VAE, so further decoder precision or memory
tuning is not supported as the next semantic fix for this case. It does not
identify whether prompt conditioning, denoising/model export, quantization or
ordinary model/seed behavior caused the result. One paired decode cannot
establish a general failure rate or prove every decoder behavior correct.

This is an assistant visual assessment, not human approval. Neither school
fidelity nor cross-scene character consistency was tested. There is still no
evidence supporting this candidate as a reliable production image path for
ASTRA.

## Execution and controlled inputs

- The manual reference-decode job succeeded. All full-image, load-only,
  preflight and SD1.5 benchmark jobs were skipped.
- All 29 offline SDXL tests passed in the live job.
- Exactly one reference PNG was produced; zero denoising steps were executed.
- Reference decode: 74.077270 seconds.
- Supervised worker elapsed: 84.841153 seconds.
- Peak sampled process-tree RSS during decode: 4,767,842,304 bytes
  (4.4404 GiB), below the unchanged 12 GiB cap.
- The 2 GiB available-RAM floor, 600-second load, 900-second decode and
  1200-second overall worker limits remained enforced.
- CPU: AMD EPYC 7763, four logical/affinity CPUs; Torch two compute threads and
  two inter-op threads. CPU float32, no tiling or slicing.
- Torch 2.14.1+cpu, Diffusers 0.39.0, NumPy 2.4.6, Pillow 11.3.0 and psutil 7.0.0.

The exact run-76 checkpoint and baseline image were used. All six pinned
source-file hashes passed before model download. The exported VAE config
identifies stabilityai/stable-diffusion-xl-base-1.0 at
462165984030d82259a11f4367a4eed129e94a7b as its source. The corresponding
reference FP32 safetensors and config passed the pinned size/hash checks,
architecture checks and complete-weight-load check.

Only the VAE was loaded; no UNet, text encoders, tokenizers or full diffusion
pipeline were loaded. The raw final scheduler latent was divided by 0.13025
exactly once and passed to AutoencoderKL.decode, followed by VaeImageProcessor.
The reference uses the recorded source weights before INT8 compression, so this
is a reference-versus-export comparison rather than bit-identical model weights.

The short duration is a decode-only measurement. It does not reduce or replace
the roughly 28-minute denoising cost measured in run 76.

## Verified artifacts and numerical comparison

| Artifact | SHA-256 |
| --- | --- |
| Original artifact ZIP | ebaa126e519850924c6d1ba0230424494b62462fffaf10588cc710fb5669d170 |
| baseline-openvino.png | 4fb3557b1183d584d5e2645987182b9a0c2971079cc3d3e733c6cd1e97d40f0e |
| reference-vae.png | ccdc87b017a9151fa6cb7c468f013919c1b713b8abe6648ce025ed07e97d5727 |
| source-latents.npy | fc53b74944c0b1b0c72f0a82743812677c8d34e1faa39d0fbac99e8f04f34c35 |

The downloaded ZIP matched GitHub's artifact digest. Both PNGs are RGB,
1024x1024; their hashes and the saved latent hash match the recorded evidence.
Independent local recomputation reproduced:

- Mean absolute per-channel pixel difference: 0.892443657 on the 0-255 scale.
- Root mean square per-channel pixel difference: 1.621609330 on the same scale.

These small differences support the observed similarity but do not constitute
a semantic pass. Both images contain many repeated vehicles, mixed viewpoints,
edge-cropped subjects and incomplete vehicle forms. The single-truck rubric
fails in both.

## Smallest next validation

Audit prompt conditioning before another full image attempt:

1. Check the exact positive/negative prompt token IDs, truncation behavior,
   hidden-state selection, pooled embedding selection and SDXL time-ID packing
   against the pinned reference implementation.
2. If the static audit does not expose a mismatch, perform one bounded CPU
   text-encoder-only comparison against the same source revision, processing
   encoders sequentially within the existing memory cap. Save shapes, finite
   checks and numerical differences for positive and negative conditioning.
3. Do not infer correctness from shapes alone or turn numerical agreement into
   image approval. If conditioning agrees, the denoiser/export/model behavior
   becomes the remaining investigation rather than further VAE changes.

That next check has not been implemented or run by this result record. No seed
sweep, model switch or repeat full denoising run was launched after this decode.

approved=false, production_ready=false, published=false and
manual_visual_review_required=true remain unchanged. Archived semantic and
character metadata remains not_verified; this document records the separate
visual failure. No automatic approval, production fallback, paid API,
publishing, merge or main integration is enabled.
