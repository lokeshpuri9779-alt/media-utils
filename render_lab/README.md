# ASTRA Render Lab — isolated experiments

This branch is for CPU/free-runner rendering benchmarks only. It is not a publishing lane.

## Rules
- Do not add YouTube credentials, publishing steps, or production state writes.
- Keep experiments in `render_lab/` and manual-only workflows.
- Do not modify production workflows on `main`.
- Measure install time, memory use, render time, resolution, motion, and output validity.
- Compare with ASTRA Main before proposing any selective integration.
- No paid API or GPU requirement; failures must be reported, not hidden.

## Initial evaluation queue
1. Record baseline environment and FFmpeg capabilities.
2. Benchmark OpenVINO/SD 1.5 on CPU only if dependencies and model licensing permit.
3. Benchmark Blender/Godot procedural animation.
4. Assemble candidate video with FFmpeg.
5. Inspect resulting MP4, frame-motion report, and failures.
6. Promote only independently verified improvements through review.
