# SDXL INT8 fixed-seed image attempt: time limit

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40744886179
Code: c31b7fecc0b926de8863e0d812af7c9bf9ea0a0b
Artifact: 12842041333, astra-sdxl-one-image-40744886179
Model: OpenVINO/stable-diffusion-xl-base-1.0-int8-ov
Model revision: d54e5b43fcb6b4b358f3a134269115d3fcb3eb25

## Result

The supervisor stopped the worker at the 600-second inference limit. Status inference_timeout, worker exit -9, supervisor elapsed 657.53 seconds. The workflow failed as intended and retained diagnostic evidence. No PNG was produced; no semantic or character review could be performed. This was not an observed memory failure.

| Stage | Seconds | Sampled peak process-tree RSS bytes |
| --- | ---: | ---: |
| Download | 37.40 | 28291072 |
| Load | 7.91 | 780189696 |
| Compile | 11.64 | 10173046784 |
| Inference | stopped at 600-second budget | 11278934016 |

Peak sampled inference RSS: 10.50 GiB, below the 12 GiB cutoff. The final progress entry was 16/20 steps at 9m55s; recent steps took approximately 37.2 seconds each. The 2 GiB available-RAM floor did not trigger. Decoding and image saving were not reached, so their memory requirements remain unknown.

## Reproducibility and limitations

Seed 42; 20 EulerDiscreteScheduler steps requested; guidance 7.5; 1024x1024; CPU; existing INT8 stored weights; f32 runtime precision hint; one stream; no further quantization or export. Initial float32 noise shape (1,4,128,128) was saved with scheduler and request settings. Its verified SHA256 is 23c72e908d9e3fbe50836a02f09ccde0acfcf28c00dec75b986c49dadf0c115e.

Positive prompt: family-friendly illustration of a single bright red toy fire truck, side view, fully visible, on a plain white background, clear colorful detailed shapes, no people, no text

Negative prompt: people, text, words, watermark, logo, blurry, deformed wheels, missing ladder

The current branch's prompt pair was preserved after concurrent single-image implementation changes. It differs from the earlier SD1.5 prompt intervention. This is a new-candidate feasibility test, not a one-variable parity comparison.

Four guardrail tests passed locally and in the workflow; ASTRA Fast CI 40744646249 passed. The worker log retained an export-detection cache-path warning, but explicit export=false remained and denoising proceeded.

## Decision

A reliable free image path is still unproven. SDXL INT8 loaded, compiled, and made steady denoising progress within the sampled memory budget, but this attempt did not complete within 10 minutes.

Smallest next validation: one separately budgeted rerun of the identical seed/noise, prompt pair, model, scheduler, resolution and step count with a 900-second inference ceiling, keeping the 12 GiB RSS cutoff, 2 GiB available-RAM floor, 1200-second overall worker ceiling, and manual review gates. Based on observed step timing, 20 denoising steps alone would take roughly 12.4 minutes; this is an estimate, not a completed render measurement. Decode time/memory and successful completion are not guaranteed. Do not reduce steps or sweep seeds to manufacture a quality pass. No rerun or time-limit increase was performed in this review.

Keep approved=false, production_ready=false, published=false, manual_visual_review_required=true. No automatic approval, production fallback, paid APIs, publishing, or merge.
