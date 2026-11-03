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

## One-shot authorization record

The exact commit message `experiment(ASTRA): one-shot offline Qwen 0.5B CPU benchmark` authorizes this single bounded experiment on the isolated branch. Later ordinary commits do not restart the large-model job.

## First real result and bounded retest

Run #41646109950 successfully built the pinned runtime, verified the exact 397,808,192-byte GGUF, and executed the local model in 17.332 seconds (520,776 KiB peak child RSS). The generated story **failed** the four-beat contract: five short placeholder beats followed by repetitive prose. This is a creative-quality failure, not an execution failure. Review-only flags remained false for approval, readiness, and publishing.

One new bounded retest uses the **same** model, seed, source revision, prompt theme, runner and time budget, but tightens the instruction and passes a strict JSON schema (exactly four 100–500-character beat strings, one title, no extra fields) to llama.cpp. The existing structural editorial gate still separately rejects short or repeated story beats. Constrained JSON can improve output shape, not guarantee causality, originality, or publication quality. No automatic retries or bigger model sweeps.

Exactly one push commit using `experiment(ASTRA): constrained JSON one-shot CPU retest` can trigger this diagnostic. The earlier one-shot authorization message no longer triggers this job.

## Constrained retest execution

Second bounded run authorized after the schema and new regression tests passed in parallel review workflow #41656088929. This does not approve the resulting story for production.

## Second real result: JSON-schema sampler failure

Run #41656194405 built pinned llama.cpp, verified the model, then exited in
0.668 s at sampler initialization with `Failed to initialize samplers:
std::exception`. No story was generated and the review contract failed.
The larger JSON schema with long-string min/max limits may have caused the
sampler failure, but the underlying exception message is insufficient to
prove that cause.

The next isolated proposal replaces the dynamic JSON-schema conversion with
a short, explicit GBNF grammar: one title and an array with exactly four JSON
string beats, in that order, with no other fields. Substantive beat length,
distinctness, causality and editorial review remain separate fail-closed
checks. This avoids claiming grammar guarantees story quality.

**No third real-model benchmark was launched in this change.** Future model
inference requires its separate explicit one-shot authorization; unit and
preflight CI checks do not download models.

### Reporting correction

The second run's `llama-cli` process exited with code 0 despite logging
`Failed to initialize samplers`. The initial benchmark script marked
`model_executed=true` based on exit code, which was misleading. The
updated harness recognizes that exact fatal marker, records
`SamplerInitializationFailed`, and keeps `model_executed=false`. A
fixture regression test locks this behavior; it does not imply a third
model run.
