# Native SDXL run 76: image completed, semantic gate failed

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41988573278
Tested commit: c26da903fc75045deaa181f6ac10c26c9ec4ebe7
Job: 127115089632
Artifact: 13397953689 (astra-sdxl-one-image-41988573278)
Artifact expires: 2026-11-12T08:09:43Z.
Review date: 2026-11-05.

## Decision

This run demonstrates that the pinned SDXL INT8 CPU path can finish one native
1024x1024 image within the existing slow-review limits after releasing unused
compiled requests. It does not establish a reliable free image path for ASTRA.
Direct inspection of the saved PNG fails the single-object semantic rubric:
the image contains many red fire trucks and vehicle fragments arranged across
the canvas instead of one centered, fully visible truck.

The assessment below is an assistant visual inspection of the actual PNG,
not human approval. The archived metadata is retained unchanged:
semantic_quality=not_verified, character_consistency=not_verified,
approved=false, production_ready=false, published=false, and
manual_visual_review_required=true.

## Measured runtime and artifact integrity

- Workflow and worker succeeded; worker exit 0 and images_generated=1.
- All 21 offline guardrail tests passed in the live job.
- Total worker elapsed: 1859.124151 seconds (30.99 minutes).
- Denoising: 20/20 steps, 1696.283305 seconds (28.27 minutes).
- Recorded inference interval: 1758.521403 seconds. Its approximately 62.24
  seconds beyond denoising includes checkpointing, cleanup, decoding,
  postprocessing and PNG writing; it is not an isolated decode timing.
- Download/load/compile: 79.145722 / 7.133473 / 12.660124 seconds.
- Peak sampled process-tree RSS: inference 11,366,912,000 bytes (10.5863 GiB),
  decode 10,517,864,448 bytes (9.7955 GiB).
- Cleanup measured worker RSS falling from 11,366,912,000 to 4,375,707,648
  bytes (10.5863 to 4.0752 GiB). This worker-only measurement differs from the
  supervisor's process-tree measurement, which can count shared pages twice.
- Limits stayed at 12 GiB RSS, 2 GiB minimum available RAM, 2400 seconds
  inference including decode, and 2700 seconds overall.
- CPU: AMD EPYC 7763, four logical/affinity CPUs; UNet two threads, one stream,
  LATENCY. The same reported CPU model and thread settings occurred in the
  previous memory-stop run; this is not proof of identical resource allocation.

The PNG opens as RGB, 1024x1024, and passes file-integrity verification.
The saved final latent is finite float32 with shape (1, 4, 128, 128).
Verified SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| Original downloaded ZIP | 4c7481f447c36d2e02ca6e415e17410dda3a7ad8ee675c9eb3178b3271dcbbf5 |
| sdxl-fixed-seed-42.png | 4fb3557b1183d584d5e2645987182b9a0c2971079cc3d3e733c6cd1e97d40f0e |
| denoised-latents.npy | fc53b74944c0b1b0c72f0a82743812677c8d34e1faa39d0fbac99e8f04f34c35 |

The PNG and latent hashes match their archived metadata. request.json,
manifest.json, scheduler.json, initial-latents.npy and conditioning.json are
byte-identical to run 41843537162. The comparison controls model files, prompt,
seed/noise, scheduler, resolution and size conditioning.

## Visual assessment

Prompt: "One red toy fire engine, one vehicle only, centered in a single
side-view composition on a white studio background, fully visible, with
attached wheels and one roof ladder."

| Criterion | Observation | Assessment |
| --- | --- | --- |
| Recognizable red toy fire engine | Several recognizable red toy fire vehicles appear | Object category present |
| Exactly one vehicle | Many vehicles and detached-looking vehicle sections fill the canvas | Fail |
| Centered, fully visible side view | Mixed viewpoints, repeated objects and vehicles cropped by image edges | Fail |
| Attached wheels and one roof ladder | Some trucks have wheels or ladders, but there is no single qualifying vehicle; several shapes are incomplete or malformed | Fail |
| White studio background | Predominantly white background | Present; insufficient for a pass |
| No duplication or major distortion | Repeated collage-like layout, incomplete bodies and fragments | Fail |
| School scene fidelity | No school was requested in this test | Untested |
| Character consistency across scenes | Only one image was generated; no identity reference or scene sequence | Untested |

The result is not a blank/noisy pixel failure. Recognizable vehicles and a
white background do not compensate for failure of count and composition.
Native resolution and completion of all 20 steps have not resolved the
duplication seen in earlier lower-resolution diagnostics. This run alone
does not identify the cause or establish a failure rate.

## Review of the benchmark changes

The final-step callback checkpoints the unscaled scheduler latent before
decoding. It releases compiled requests for the UNet, both text encoders and
the unused VAE encoder, retaining the VAE decoder. The callback returns the
same latent payload, and the normal pipeline still performs latent scaling,
decoding and postprocessing. The supervisor counts decode against the
original inference deadline rather than starting a fresh timebox.

This run supports the resource-management change: a completed PNG and the
memory measurements now exist. Tests cover checkpoint preservation, cleanup
timing, leaving the decoder intact, failure propagation and deadline handling.
Neither passing tests nor a successful workflow is a semantic quality gate.

The workflow remains manually dispatched and review-only, with paid access
disabled and no production integration added by these benchmark changes.
PR #864 was still an open draft, unmerged, with auto-merge unset when checked.

## Smallest next diagnostic

Use this saved final latent for one decode-only reference comparison before
another full denoising attempt:

1. Verify provenance and configuration of a matching reference SDXL VAE.
   Record its immutable revision and weight hashes. A different or unverified
   VAE would confound the comparison.
2. Verify the archived latent hash, shape, dtype and finite values. Decode
   only that tensor, applying the recorded 0.13025 latent scaling exactly
   once and matching the existing image postprocessing. Record the exact
   decoder and runtime used.
3. Save the reference PNG, hash, runtime and memory evidence and visually
   compare object count, composition and vehicle geometry with this PNG.
   Numerical differences alone are not evidence of a semantic correction.
4. If both retain the many-truck layout, investigate denoiser/conditioning or
   model-export behavior next. If the layout differs substantially, examine
   the decoder implementation and model/configuration parity before drawing
   a causal conclusion. Failure to establish matching provenance leaves the
   diagnostic inconclusive.

This proposed comparison requires no prompt/seed sweep and no repeat of the
28-minute denoising stage. Use CPU-only execution within the existing memory
limits and a bounded manual timebox. It has not been run or enabled here.

Even a corrected single-truck result would need human review, then a separate
small scene-fidelity and identity-continuity check before broader reliability
claims. No automatic approval, production fallback, paid API, publishing,
merge or main integration is enabled by this review.
