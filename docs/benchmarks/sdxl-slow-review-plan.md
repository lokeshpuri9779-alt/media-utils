# One bounded slow SDXL image review

## Decision and correction

Run 41838601016 validated the three-step early stop, not image quality: its
projection was 2066.06 seconds, exceeding our 900-second diagnostic cap.
The recommendation in sdxl-budget-check-41838601016.md to find a known fast free
CPU while preserving that cap is superseded by this explicit slow-review option.
The earlier measurements and failure assessment remain unchanged.

GitHub documents standard public-repository Linux x64 runners with 4 CPUs and
16 GB RAM, free for public repositories; its published standard labels select
OS/architecture, not a specific Intel Xeon or AMD EPYC model. This repository's
runs have already demonstrated materially different CPU models and timings.
GitHub's hosted-job execution limit is six hours, so our 15-minute inference
cutoff is an experiment choice rather than the platform limit.

Sources checked 2026-11-04:
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/actions/reference/limits
- https://docs.openvino.ai/nightly/openvino-workflow/running-inference/inference-devices-and-modes/cpu-device/performance-hint-and-thread-scheduling.html

OpenVINO's LATENCY mode normally avoids using both hyperthreads for a single
request. Two effective inference threads on four logical CPUs is not, on its
own, proof of an incorrect setting. CPU topology has not been established for
every recorded run. No speculative thread or precision change is made.

## Explicit experimental mode

Select the PR branch, enter BENCHMARK_SLOW_REVIEW, set sdxl_one_image=true and
sdxl_load=false, and leave other diagnostic selections false. This runs exactly
one attempt with --one-image --slow-review. There is no retry loop or schedule.
BENCHMARK retains the original normal and timing-probe behavior.

| Limit | Normal image | Explicit slow review |
| --- | ---: | ---: |
| Inference | 900 s | 2400 s (40 min) |
| Overall worker | 1200 s | 2700 s (45 min) |
| Load/compile | 600 s | 600 s |
| Sampled process-tree RSS | 12 GiB | 12 GiB |
| Available RAM floor | 2 GiB | 2 GiB |
| Workflow job | 40 min | 65 min |

The job timebox leaves room for the existing 15-minute dependency-install limit,
45-minute worker, checkout, tests and artifact upload. The 450-second no-image
timing probe is unchanged. Slow-review mode rejects load-only and timing-probe
combinations before any download or subprocess launch.

The first-three-step projection uses the selected inference cap and still stops
an over-budget attempt. The 180-second decode reserve is an engineering margin,
not measured decode time or a completion guarantee. The supervisor independently
enforces the hard limits even after a favorable projection.

The pinned model/revision, prompt, negative prompt, seed 42, initial noise,
1024 resolution, spatial conditioning, 20-step schedule, guidance, precision,
and thread configuration are unchanged. Only the explicit review timebox grows.

## Next evidence and stop rule

Collect one native-resolution output if the bounded run completes. Compare its
request, manifest, scheduler, conditioning and initial-noise artifacts to run
41838601016. Review the output against the existing one-truck rubric: exactly
one recognizable red toy fire engine, attached wheels, one roof ladder, side
view, one white studio background, no panels, duplication or major distortion.
If it fails or times out, record that outcome before proposing any further run.

A completed image is only a candidate for manual review. A single good truck
does not establish reliability, school-scene fidelity, or character identity
across scenes. approved=false, production_ready=false, published=false and
manual_visual_review_required=true remain mandatory. No automatic approval,
production fallback, paid API, publication, main integration or merge is added.
