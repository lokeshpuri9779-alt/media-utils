# Square-resolution diagnostic: improved composition, semantic gate still failed

Reviewed 27 October 2026. Assistant visual assessment of both original PNGs; not a human approval receipt.

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40479544955
Code revision: 28e9d6287dbdeaf65b2559245f3023f2cd9d4f53
Artifact: astra-openvino-cpu-40479544955, ID 12722462769, expires 3 November 2026.
Baseline: run 40415382474, its two 20-step portrait cases.

## Controls and limitations

Same original prompt (including the words "portrait composition"), seeds 42 and 123, 20 steps, guidance 7.5, CPU FP32 hint, no automatic 8-bit compression, model revision 451f4fe16113bff5a5d2269ed5ad43b0592e9a14 and identical recorded PNDMScheduler configuration. Core package versions match the baseline: diffusers, torch, torchvision, openvino, openvino-tokenizers, pillow, transformers, numpy, optimum, optimum-intel and huggingface_hub.

Image dimensions changed from 512x768 to 512x512. Changing dimensions changes latent tensor shape; the same seed does not imply identical initial noise across shapes. Separate hosted runs do not establish a controlled hardware speedup. This small test supports an association between native resolution and improved composition, not proof that resolution alone caused the earlier failures.

Square images are diagnostic-only and portrait_scene_eligible=false. The shared production portrait gate was not changed.

## Inspection

| Seed | Inference seconds | Pixel result | Assistant visual assessment |
| --- | --- | --- | --- |
| 42 | 134.50 | Pass | One dominant red truck and coherent trees; fewer duplicates than baseline. The small red garage-like structure is floating/disconnected, not an identifiable yellow school. Faint text-like marks are visible. Full prompt fails. |
| 123 | 132.96 | Pass | Fewer scattered duplicates, but the foreground truck is cropped and fused with a tall building-like red form. Background structure is red, not an identifiable yellow school. Full prompt fails. |

Both images fail the mandatory yellow-school scene requirement. No character-continuity evidence was produced. Cleaner image structure must not be translated into approval.

Setup: 120.93 seconds. Benchmark process: 388.61 seconds (6.48 minutes), excluding dependency installation and other workflow steps. Peak process RSS: 11,992,880 KiB (11.44 GiB).
Mean inference: 133.73 seconds; prior portrait 20-step mean: 337.39 seconds. These are observed run timings, not a guaranteed throughput improvement.

## Decision and next bounded question

Keep approved=false, production_ready=false, published=false, manual_visual_review_required=true. No production fallback, paid API or publishing. Do not run the conditional character-consistency test because the semantic prerequisite still fails.

Resolution-only correction is insufficient. If continuing this candidate, the next useful diagnostic is object isolation at 512x512: one prompt for a single red toy fire truck and one for an identifiable yellow school building, using fixed recorded settings. This would distinguish basic object-generation failures from failure to compose the two objects together. It is not authorized production artwork and would not establish reliability even if both passed. Do not spend more runs repeating the unchanged compound prompt.

## Image hashes

- seed-42-steps-20.png: 28f4216b16bbbf9bfe241dff3c25782fd81b818c4dd9c8e5f3b29c419b46142e
- seed-123-steps-20.png: c85410932fbf80f249c92907eeeb54c8ccb57991290ab257bcfd293a8f159f8e
