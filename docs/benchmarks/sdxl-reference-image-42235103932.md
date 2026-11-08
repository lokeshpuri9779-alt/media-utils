# SDXL reference-conditioned image: semantic failure

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/42235103932
Code: d4094344e7b1940bc3e48e7469a6d02833d9dcb9
Artifact: astra-sdxl-reference-image-42235103932 (13514641401)

## Result

The workflow completed successfully, but assistant visual inspection of the actual 1024×1024 PNG fails the single-object composition rubric. The image contains many red fire trucks, distorted vehicle fragments, multiple viewpoints and objects cropped at the edges. It is not one centered, fully visible side-view toy fire engine with attached wheels and one roof ladder. This is an assistant assessment, not human approval.

Compared side by side with run 41988573278, reference FP32 text conditioning preserves the same broad collage failure. The images are not identical: RGB pixel MAE is 8.859790/255 and RMSE 19.820395/255. These pixel differences are descriptive only and do not establish semantic quality.

## Controlled change and verification

The run substitutes the source FP32 text-conditioning tensors from run 42192924660 while retaining the pinned INT8 OpenVINO denoiser, native decoder, seed 42, exact prompt and negative prompt, 1024-square resolution, 20 Euler steps and guidance 7.5. It resumes with the verified first prediction from run 42232753910 and completes 19 live predictions. The trajectory records all 20 timesteps, 951 through 1, with source tensor and first-input hashes validated.

The archived report records one generated image, worker exit 0, elapsed 1820.922663 seconds (30.35 minutes), peak sampled process-tree RSS 11,294,789,632 bytes (10.52 GiB), below the 12 GiB cap. Shared pages may be counted more than once. The implementation had 37 passing offline tests before dispatch. These establish execution and guardrail behavior, not image fidelity.

SHA-256:
- ZIP: 2e9162369a85d41cd714ff0b522a46a8fa3251e4d1ac4a4f73b6702ab60e2bf5
- PNG: 3baff991e87c396c9d698e130e4015ea1ed8e0adea8ae2dc50b97ed920496708

ZIP digest and PNG digest were independently checked after download. The archive includes request, runtime, conditioning, scheduler, trajectory, latent, image and resource reports.

## Interpretation and smallest next validation

Evidence still does not support a reliable free ASTRA image path. Reference decoding in run 42034690654 and reference text conditioning here each failed to repair this case. This narrows the investigation but does not prove that denoiser quantization is the root cause; the denoiser, scheduler interaction and other pipeline behavior remain candidates.

The smallest discriminating next check is a bounded, no-image comparison of the reference FP32 denoiser and current INT8 denoiser on the saved first-step sample, timestep and reference conditioning. First perform a disk/RAM feasibility check; do not exceed the existing resource caps or silently change precision. Compare negative, positive, guidance-residual and guided predictions, retaining raw outputs. Numerical divergence would motivate one controlled full-trajectory reference-denoiser image; numerical agreement at one step would not exonerate later-step behavior. Do not run a broad seed sweep before establishing a useful diagnostic.

A reliable path would still require recognizable scene elements (including a school when requested), separate cross-scene character-consistency checks, and repeated human-reviewed semantic successes. None is established by this isolated truck test.

## Release state

approved=false
production_ready=false
published=false
manual_visual_review_required=true

Archived semantic_quality and character_consistency remain not_verified. This report adds the explicit visual failure without rewriting raw machine evidence. No automatic approval, production fallback, paid API, merge or content publishing is enabled.
