# Native-resolution SDXL control: run 40892163644

## Decision

The 1024x1024 control hit its 900-second inference limit without producing a PNG. No visual conclusion can be drawn at native resolution. A reliable free ASTRA image path remains unproven. Stop resolution, prompt and timeout sweeps; do not promote this path.

## Evidence

- [Run](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40892163644), tested commit d12325f92bea3f3c2b20051ef66355897df534f8.
- Artifact 12905908460, astra-sdxl-one-image-40892163644; expires 2026-11-05 14:47:13 UTC.
- Dependency installation succeeded in 49 seconds. Six offline guardrails passed. The image step failed; evidence upload succeeded.
- report.json: status=inference_timeout, worker_exit_code=-9, images_generated=0, worker elapsed 945.346 seconds.
- The supervisor killed the worker at the inference limit. This was not a reported OOM or dependency installation failure.
- Download 24.954s, load 6.629s, compile 12.863s.
- Sampled peak process-tree RSS 11,363,131,392 bytes (10.583 GiB), below the unchanged 12 GiB cap.
- Last denoising progress: 9/20 at 13m51s, approximately 92.3 seconds per step. No image-review.json, worker-result.json or PNG exists in the artifact.
- At that observed rate, 20 denoising steps alone would take roughly 31 minutes, before decode. This is an estimate, not a completed runtime.
- The prior native-resolution run 40744886179 reached 16/20 in 600 seconds with approximately 37-second steps. Across-run variability makes extrapolated deadlines unreliable; hardware/thread information is insufficient to attribute this slowdown.

## Configuration checks

Same pinned model revision d54e5b43fcb6b4b358f3a134269115d3fcb3eb25. manifest.json and scheduler.json are byte-identical to the completed 512x512 prompt control 40854430774. Prompt, negative prompt, steps=20, guidance=7.5 and seed=42 are unchanged.

conditioning.json records:
- original_size and target_size: [1024,1024]
- crop: [0,0]
- positive and negative time IDs: [[1024,1024,0,0,1024,1024]]
- VAE spatial scale 8; amplitude scaling factor 0.13025
- UNet sample size 128
- latent shape [1,4,128,128]
- scheduler initial noise sigma before the inference call: 14.648818969726562

The saved latent array shape and raw SHA-256 were independently checked:
23c72e908d9e3fbe50836a02f09ccde0acfcf28c00dec75b986c49dadf0c115e.

The conditioning artifact captures values computed before the call and the explicitly supplied conditioning arguments; it is not a trace of every tensor inside inference. The larger latent shape means seed 42 does not imply byte-identical noise to the 512 control.

## What this establishes

The model loads and denoises within the memory budget, but this native-resolution attempt did not finish within its time budget. The latest completed 512 images still fail object count/composition. Native-resolution semantics, school-building fidelity and cross-scene character consistency remain unverified.

## Smallest next validation

Do not immediately raise the timeout or launch another full image. First obtain a bounded CPU performance diagnostic: record runner CPU model, available/affinity CPU count, cgroup CPU quota, OpenVINO effective inference thread settings, and per-step timing under the same pinned configuration. Prefer existing job evidence; if it lacks these fields, a separately designed short diagnostic should stop after a small fixed number of denoising steps and produce no approved media. Its purpose is to explain or bound the 37s-versus-92s step-time variability before spending another full-image budget. Such a diagnostic has not been launched here.

This performance check cannot validate semantics. A completed image and manual review would still be needed before any story/identity testing.

approved=false; production_ready=false; published=false; manual_visual_review_required=true. No automatic approval, production fallback, paid API, publishing or merge was enabled.
