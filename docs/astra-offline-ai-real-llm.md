# ASTRA: bounded real offline GGUF inference (experimental)

This is the next evidence gate after draft PR #951's three CPU-friendly
contract-review lanes passed. It does **not** alter ASTRA Main.

## Immutable inputs

- Model: `bartowski/Qwen2.5-0.5B-Instruct-GGUF`, file
  `Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`, 398 MB, Apache-2.0.
- SHA256: `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`.
- llama.cpp: tag `b12064`, verified commit
  `51fe42c5d14bfb9adf0612ff98a9ab79e0e7275c`.
- Two CPU threads, zero GPU layers, max 700 generated tokens,
  2048-token context, seeded, one prompt, 180-second inference timeout.
- Max GitHub Actions job duration: 17 minutes, memory ceiling on the
  subprocess: 6 GiB virtual address space.

## Run conditions

The workflow `.github/workflows/astra-offline-ai-oneshot.yml` only runs
real inference for one exact experimental-branch **push commit message**
or a deliberate manual `BENCHMARK` workflow_dispatch. No scheduled or
PR-triggered real inference. A failed or skipped run must not be conflated
with a passing model benchmark. GitHub Actions minutes are consumed.

The job downloads and verifies the model *before* CPU-local inference.
Therefore inference is offline; initial setup still needs internet access.

## Evidence, not production readiness

On successful executable completion, generated text is archived for manual
inspection. `review-report.json` separates model execution from passing
a structural four-beat story contract. Review JSON (if it exists) explicitly
keeps `approved=false`, `production_ready=false`, `published=false`.
A structural pass is not proof of creative quality, originality or character
consistency. Neither the image route nor ASTRA publishing is changed.

If this model fails the structure contract, the job fails closed while keeping
bounded raw output and status evidence for debugging. The next experiment
must be justified using these real results; do not automatically retry with
larger models, API calls, or expensive multi-seed sweeps.
