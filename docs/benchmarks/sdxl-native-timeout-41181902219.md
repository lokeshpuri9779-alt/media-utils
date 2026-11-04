# Native SDXL full-image attempt: timeout on the recorded AMD runner

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41181902219
Tested commit: `b4bac02f20a7d15240f878a725b9244f90799084`.
Artifact: `13035643107`, `astra-sdxl-one-image-41181902219`.
Downloaded ZIP SHA256 verified: `1deba71f150d961e5af7dbcdde66c1de46ec8cad6f667792570fb146d35e51d5`.
Artifact expires 2026-11-07 08:03:02 UTC (13:33:02 IST).

## Result

The full-image step failed with `inference_timeout`. The supervisor terminated the worker at the existing 900-second inference limit; worker exit was -9. The last completed progress entry was 10/20 at 14:03, with a displayed estimate of 84.19 seconds per step. Worker elapsed including setup was 948.570 seconds.

No PNG, image-review record, or completed worker-result is present. The report records zero images. There is no new visual evidence to evaluate, and the timeout does not establish whether native-resolution semantic fidelity would pass or fail.

Runtime installation succeeded in about 52 seconds; all 11 offline guardrail tests passed; evidence upload succeeded. The performance-only step and other benchmark jobs were skipped. This failure was not the previous empty callback-list error.

| Measurement | Full image run |
|---|---|
| CPU model | AMD EPYC 7763 64-Core Processor |
| Available logical / affinity CPUs | 4 / 4 |
| Effective UNet inference threads / streams | 2 / 1 |
| Effective UNet hint / device | LATENCY / CPU |
| Torch intra-op / inter-op threads | 2 / 4 |
| Peak sampled process-tree RSS | 11,366,002,688 bytes, 10.585 GiB |
| Download / load / compile | 27.775 / 7.188 / 12.819 seconds |
| Inference / worker deadlines | 900 / 1200 seconds |
| RSS cap / available-RAM floor | 12 GiB / 2 GiB |
| Images generated | 0 |

RSS is sampled every 0.2 seconds and can count shared pages more than once. The reported termination reason was the time limit, not either memory guard. Two readable cgroup ancestors had `cpu.max=max 100000`; root/effective quota remains unavailable, not proven unlimited.

## Comparison with the successful short probe

Probe https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41085142440 recorded Intel Xeon Platinum 8573C, four available CPUs, two effective UNet threads and one stream. Its later callback intervals were 33.079 and 33.216 seconds.

Direct byte comparisons confirm that `request.json`, `manifest.json`, `scheduler.json`, `initial-latents.npy`, and `conditioning.json` are identical between this full run and that probe. They are also identical to the previous native timeout run 40892163644. The request is 1024x1024, 20-step Euler, seed 42, guidance 7.5 and the same single red toy fire-engine prompt. Initial noise hash is `23c72e908d9e3fbe50836a02f09ccde0acfcf28c00dec75b986c49dadf0c115e`.

Core runtime versions in the full job logs match the configured pins: Torch 2.14.1+cpu, OpenVINO 2026.4.1, optimum-intel 2.2.0, Diffusers 0.39.0, Transformers 4.57.6 and NumPy 2.4.6. This is not a claim that all transitive dependencies or runner conditions were identical.

The observed speeds differ by roughly 2.5 times. CPU model and Torch inter-op count also differ, and these are separate machines and executions. This is an association, not a controlled demonstration that CPU architecture or thread count caused the difference. No throughput samples exist from the earlier failed AMD callback probe.

At the displayed 84.19 seconds per step, 20 steps would take roughly 28.1 minutes before decoding. That is an extrapolation, not measured completion, and it exceeds the present budget. The earlier approximately 11-minute projection from an Intel probe did not transfer to this AMD run.

## Decision and smallest next validation

A reliable free image path for ASTRA is still unsupported by the evidence. The short probe proved limited execution on one runner; full native completion remains unverified, and earlier 512px images failed the single-object composition requirement. School fidelity and cross-image character consistency remain unverified.

Stop unchanged full-run retries based on timing from a different runner. The smallest useful next change is to measure the first three denoising steps inside the same full-image pipeline call and process, then continue the remaining 17 steps only if the observed timing fits the existing budget with explicit decode headroom. Preserve the original 20-step schedule and latent state; do not launch a separate job or restart inference after the probe.

A concrete proposed early-stop rule is:
- At callback three, estimate total inference as elapsed time since inference-stage start + 17 times the slower of intervals two and three + 180 seconds reserved for decoding/output.
- If that estimate exceeds 900 seconds, stop with an explicit diagnostic budget-exceeded result, zero images and all approval flags false.
- Otherwise continue in the same call, still subject to the existing hard time and memory limits. The 180-second reserve is a proposed engineering margin, not measured decode latency or a completion guarantee.
- Make one attempt, with no automatic retry, CPU-selection loop, model/prompt/seed/thread sweep, or raised resource limits.
- If a PNG is produced, inspect for one recognizable red toy fire engine, attached wheels, a roof ladder, side-view composition and a single white background. Duplication, panels, missing features or distortion fail this diagnostic.

This is a proposed next validation, not implemented or dispatched by this review. A runtime continuation decision must never approve an image. Even one acceptable truck would justify further controlled semantic and consistency validation, not production use.

## Gates

`production_ready=false`, `approved=false`, `published=false`; manual visual review remains required. Semantic quality and character consistency remain unverified. No automatic approval, production fallback, paid API, merge or publishing was enabled.
