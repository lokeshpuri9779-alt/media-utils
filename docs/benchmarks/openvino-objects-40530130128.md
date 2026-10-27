# CPU OpenVINO isolated-object review

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40530130128

Code: `4768d09d637e44d784d973e5a09fd7ce5fa4e766`. Artifact: `12746721523` (`astra-openvino-cpu-40530130128`), expires 2026-11-03. Both original PNGs were visually inspected; their SHA-256 values match comparison.json.

## Conditions

SD1.5 revision `451f4fe16113bff5a5d2269ed5ad43b0592e9a14`, CPU FP32 with automatic 8-bit disabled, PNDM, guidance 7.5, seed 42, 20 steps, 512x512. Each case has its own prompt in comparison.json. The top-level prompt retains the earlier combined scene and must not be mistaken for these cases' actual inputs.

Both prompts request a single fully visible object on a plain white background, with no people or text. Truck: bright red toy fire truck, side view. School: yellow school building, front view.

## Findings

| Case | Technical pixel check | Manual prompt-fidelity review | Inference |
| --- | --- | --- | --- |
| truck-only | Pass | Fail: a large red truck-like vehicle, a separate smaller red vehicle, and detached ladder/wheel-like structure. Multiple objects and teal background violate the requested single truck and white background. | 209.48 s |
| school-only | Pass | Fail: recognizable yellow building, but school identity is ambiguous without relying on garbled sign-like lettering. Lettering violates no-text; trees, sky and lawn violate plain white background. | 207.20 s |

No obvious people are visible in either image. The yellow-building concept is partially represented; that is not a full semantic pass. No recurring character was tested.

Setup: 97.24 s. Benchmark process: 514.11 s. Peak RSS: 12,448,936 KiB (11.87 GiB). These times are observations on this runner, not a throughput guarantee.

Image hashes:

- truck-only.png: `533392bdd0c8007d8e52fded9abd25b3f9d692a0ae469fa67e4f1a62ee941f32`
- school-only.png: `452e6ba8d1142d909c7c65a2e352c9b6a35b1e9211f29ad16d431af7059d13fd`

## Decision

This is executable CPU image generation, but the accumulated evidence does not support a reliable free ASTRA scene-generation path. Simple isolated prompts still fail, so composition alone cannot explain all observed failures. The experiment does not distinguish model/prompt limitations from conversion or runtime differences.

Keep `approved=false`, `production_ready=false`, `published=false` and manual visual review required. The machine report correctly leaves semantic quality and character continuity unverified; this document supplies the separate manual review. Square outputs remain ineligible for portrait scenes. No automatic approval, production fallback, paid API, publishing or main-branch integration is authorized by these results.

## Smallest next validation

Before another prompt/step sweep, perform one bounded backend-parity pair for the truck-only prompt: original PyTorch Diffusers CPU FP32 versus the OpenVINO export, using the same pinned model and compatible package versions, scheduler configuration, dimensions, guidance and 20 steps. Generate and save the initial latent tensor once and feed identical copies to both backends; equal integer seeds alone do not establish equivalent random inputs. Record latent hash, exact prompts, configurations, output hashes, time and memory. Avoid hidden prompt rewriting or negative-prompt differences. Run sequentially to limit peak memory; fail closed on timeout or memory exhaustion.

Manually compare object count, coherent attached vehicle parts, background and text artifacts in both outputs. Numerical differences alone do not establish semantic quality. If PyTorch succeeds while OpenVINO fails, investigate export/runtime parity; if both fail similarly, stop treating conversion as the leading explanation and reassess the model/prompt candidate. If both succeed, require a second seed and combined-scene validation before attempting character continuity. One successful pair would still not prove production reliability or sustained zero-cost capacity.
