# CPU environment probe review: 40922073813

## Finding

The existing CPU probe completed successfully but does not explain the SDXL slowdown. Do not infer the hardware or effective thread count of an earlier image run from this separate runner.

- [Probe run](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40922073813)
- Artifact 12919610301, astra-cpu-runtime-40922073813
- Tested commit 3203c694f0d5e75ca1598268b99c0d82c905ff2d on main; this review did not launch or merge it.
- CPU model string: AMD EPYC 7763 64-Core Processor.
- Logical CPUs available to the environment: 4.
- Affinity IDs: [0,1,2,3]; affinity count: 4.
- cgroup v1/v2 quota fields and normalized quota: null.
- Captured thread-related environment variables: none.
- Available memory at capture: 15,430,516 KiB.
- images_generated=0, approved=false, production_ready=false, published=false.

The host product name does not grant 64 cores to this job. Null quota fields mean the probe did not obtain quota information; they do not establish unlimited CPU. An empty environment-variable map does not establish the effective OpenVINO inference thread count.

The completed job logs for native-resolution run 40892163644 contain no lscpu, affinity, cpu.max or effective INFERENCE_NUM_THREADS evidence. That run used about 92 seconds per denoising step; earlier native-resolution run 40744886179 used about 37 seconds. Cause remains undetermined.

## Smallest useful next validation

One isolated performance probe, not another full image:

1. Retain model revision d54e5b43fcb6b4b358f3a134269115d3fcb3eb25, 1024x1024 shape, current prompt, seed 42, guidance 7.5, Euler scheduler and original 20-step timestep schedule.
2. Capture CPU model, affinity, cgroup membership and readable quota limits on that same runner. Record unavailable fields as unknown.
3. After compilation, read supported effective properties from the compiled UNet: INFERENCE_NUM_THREADS, NUM_STREAMS, PERFORMANCE_HINT and EXECUTION_DEVICES. Capture PyTorch intra/inter-op thread counts without changing them.
4. Measure the first three denoising callbacks with monotonic timestamps. Preserve the 20-step schedule: requesting a three-step schedule would change the work being compared. Label first-step timing as including prompt/setup overhead; steps two and three are the more useful steady-state observations.
5. Stop deliberately at callback three before VAE decode, and request latent output as an additional no-image guard. Save timing/runner metadata only; distinguish deliberate completion from errors. Do not save or approve a PNG.
6. Use a 450-second inference cap, unchanged 12 GiB RSS cap and 2 GiB available-memory floor. Keep a bounded load/compile and overall budget; preserve partial evidence on timeout.
7. Verify offline that callback three stops execution, unexpected exceptions remain failures, no image decode/save occurs, and approval/publication flags remain false.

This specification is prepared; no new probe was implemented or launched in this review. Existing concurrent changes on PR #864 were preserved. Inspect current branch state again before implementing it.

A three-step timing result can bound performance on that runner, but cannot prove the cause of historical variation or validate semantic fidelity. Current evidence still does not support reliable free ASTRA story images. Manual visual review remains required. No automatic approval, production fallback, paid APIs, publishing, merge, or timeout sweep is authorized by this report.
