# CPU OpenVINO comparison: semantic gate failed

Reviewed 27 October 2026. This is an assistant visual assessment of all four original PNGs, not a human approval receipt.

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40415382474
Code: 93fbc8a0f4e3a08524a83d0d38ebc736b3b0bd28
Artifact: astra-openvino-cpu-40415382474 (ID 12695489629; expires 2 November 2026)
Model: stable-diffusion-v1-5/stable-diffusion-v1-5
Model revision: 451f4fe16113bff5a5d2269ed5ad43b0592e9a14
Settings: CPU, FP32 hint, automatic 8-bit compression disabled, 512x768, PNDMScheduler, guidance 7.5.
The artifact comparison.json records installed packages and full scheduler configuration.

## Results

| Seed | Steps | Inference seconds | Pixel gate | Visual semantic assessment |
| --- | --- | --- | --- | --- |
| 42 | 8 | 159.33 | Pass | Fail: multiple malformed vehicles distributed through the trees/sky; no recognizable yellow school beside the truck. |
| 42 | 20 | 337.43 | Pass | Fail: cleaner main red truck, but repeated/floating vehicle forms, incoherent scene layout and no identifiable yellow school. |
| 123 | 8 | 157.20 | Pass | Fail: many distorted vehicles and small figures; school absent or unidentifiable. |
| 123 | 20 | 337.35 | Pass | Fail: cleaner collage of multiple vehicles, including a yellow vehicle rather than an identifiable yellow school; several figures violate the no-people request. |

Prompt: family-friendly illustration of a bright red toy fire truck parked beside a yellow school building on a sunny day, blue sky, green trees, clear colorful detailed shapes, portrait composition, no people, no text

Both step counts fail the scene requirements for both recorded seeds. Increased steps improve shape clarity but do not establish semantic reliability. Four pixel passes must not be interpreted as four usable scene images.

Setup was 138.74 seconds. Total benchmark process time was 1130.62 seconds (18.84 minutes), excluding dependency installation and other job steps. Peak process RSS was 13,278,996 KiB (approximately 12.66 GiB); this is a process high-water mark, not per-image incremental memory. Twenty-step inference averaged 337.39 seconds versus 158.27 seconds at eight steps, approximately 2.13 times as long.

## Decision

Stop this validation stage. Do not run the conditional two-scene character test: its prerequisite was semantic success at one setting for both seeds, and that prerequisite failed. Character continuity remains untested.

Retain approved=false, production_ready=false, published=false, and manual_visual_review_required=true. Do not create approval receipts, connect production fallback, enable paid APIs or publish. Original benchmark JSON remains unchanged; this assessment is recorded separately.

The result supports CPU execution feasibility, not a reliable free ASTRA image path. It does not establish that all CPU models or settings fail. If revisited, require one explicit, testable change to the candidate before consuming further runner time; another unchanged rerun is not warranted.

## Image identity

- seed-42-steps-8.png: 9103b1416d485774fe34fb268695b21275050472df72e334196bcf406530a680
- seed-42-steps-20.png: 4bbb63e5900d527179a7334359324134cad26a320f0f516bc0702cad6cf310c5
- seed-123-steps-8.png: ec6a42a811dc3fd05716ff2b81317cadaa9458363634c6762df7ade0e874d4df
- seed-123-steps-20.png: d9f920b21efe39e94fb1b90ac88769f09b21dd78d73ec2d591f1303b4f212497
