# SDXL same-process budget validation: run 41838601016

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41838601016
Tested commit: 9457eb6d4fc20e8e3655e328253bcd10bb000503
Job: 126603936995
Artifact: 13326844697 (astra-sdxl-one-image-41838601016)
Archive SHA-256: 63a0e69b13e4d644f4fc74ca50a4cb845d2c6636ad23e7a1d79618ac3050c164
Artifact expires: 2026-11-11 19:07:02 IST.

## Result

The full-image attempt stopped deliberately after three callback-completed denoising steps. inference-budget.json records inference_budget_exceeded; worker.log ends in that exact RuntimeError. The supervisor reports worker_failed with exit code 1, not an inference timeout. GitHub marks the job failed, as expected for this rejection.

- Step intervals: 95.038789, 93.052451, 94.331409 seconds. First interval includes setup before the callback.
- Elapsed at decision: 282.422649 seconds.
- Projected total: 2066.056598 seconds (34.43 minutes), including a 180-second engineering decode reserve, versus the 900-second limit.
- Formula: elapsed + 17 * max(second interval, third interval) + 180.
- Total worker elapsed: 377.672386 seconds.
- Peak sampled process-tree RSS: 11,366,461,440 bytes (10.586 GiB), below 12 GiB. Shared pages may be counted more than once.
- Download/load/compile: 71.797298 / 7.540669 / 13.203238 seconds.
- Images generated: 0. No PNG or decoded-image review is available.
- All 12 offline guardrail tests passed in the live job; artifact upload succeeded.

Runtime: AMD EPYC 9V74, four logical/affinity CPUs, UNet two inference threads, one stream, LATENCY, CPU; Torch threads 2/inter-op 4. Readable cgroup ancestors report max 100000; effective quota remains unknown. CPU differences do not establish the cause of runtime variation.

The progress bar shows 2/20 because the third callback raises before the progress-bar update; the three recorded callback intervals establish completion of three steps.

## Controls and interpretation

request.json, manifest.json, scheduler.json, initial-latents.npy, and conditioning.json were byte-identical to run 41181902219. The pinned model, seed 42, native 1024 resolution, 20-step schedule, prompt, and initial noise were preserved.

This validates the early-stop branch on real inference. It does not validate the continuation branch through final decoding or improve the evidence for semantic fidelity. The projection is not a measured completion time, and the decode reserve is not a guarantee.

approved=false, production_ready=false, published=false, manual_visual_review_required=true. Semantic quality and character consistency remain not_verified. No automatic approval, production fallback, paid API, publishing, or main integration was enabled.

## Smallest next validation

Do not repeat blind full-image runs on variable hosted runners. The remaining image feasibility question requires one unchanged 1024/20-step attempt on a known free CPU environment that can pass the existing same-process timing check, within the same memory and time limits. Record the runtime and preserve all input hashes; continue the same call only if its own first-three-step projection fits. Do not raise limits or automatically retry to obtain a favorable runner.

If it completes, manually assess the one-truck rubric before any wider semantic/character-consistency benchmark. A single good truck still cannot establish reliable ASTRA imagery or recurring character identity. If no suitable free environment is available, record this path as blocked under the present budget rather than treating technical checks as production readiness.
