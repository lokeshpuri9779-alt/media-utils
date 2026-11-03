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

## Unified parallel GBNF run

ASTRA uses `.github/workflows/astra-offline-ai-parallel.yml` as its single
coordinating experimental workflow. Its story, image and motion test matrix
runs in parallel; the aggregate gate verifies all three reports. **Only a
successful aggregate** permits the one real CPU GGUF inference job to start,
and only when the isolated branch push uses the exact one-shot commit message
`experiment(ASTRA): unified parallel GBNF CPU validation`. PR triggers
and ordinary pushes cannot run real model inference.

The legacy `.github/workflows/astra-offline-ai-oneshot.yml` retains
manual-only `BENCHMARK` dispatch for diagnostics and no longer responds to
push commits. It is not invoked as part of this run.

The real job still uses the same checksum-verified 0.5B model, pinned
llama.cpp source, 2 CPU threads, 700-token ceiling, 180-second process
timeout and 17-minute job deadline. New for this experiment: the
`--grammar-file` adapter enforces JSON *structure*, but it cannot prove
originality, causality, or production suitability. Approval and publishing
remain disabled.

Once a run finishes, use `review-report.json` plus raw generated output
to evaluate model execution separately from structural contract and
human narrative quality. Do not automatically retry or merge.

## Unified one-shot GBNF execution authorization

The consolidated review workflow was validated in [PR run #41659902726](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41659902726): story, image, motion and aggregate passed, and the real-model job correctly skipped because the review event was not the authorized push. One run on the experimental branch now uses the exact commit message `experiment(ASTRA): unified parallel GBNF CPU validation`; it runs the same three lanes plus an aggregate check, and only then permits one bounded CPU model inference. This authorization does not grant publication, automatic approval, paid API use, or production fallback.

## Unified-run concurrency fix and retry

The initial authorized push run #41660012605 was canceled before reaching inference because a concurrent PR validation for the same SHA shared its concurrency group. No third model output was produced. The workflow now scopes concurrency by event name and GitHub ref; PR checks can no longer cancel the authorized push run. The corrected review-only PR run #41660153898 passed all three parallel lanes and the aggregate. This one-time retry is authorized using the same exact commit-message guard; no extra prompts, models or production permissions are introduced.

## Third real run: grammar worked, story quality failed

[Unified run #41660334335](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41660334335)
completed successfully with three parallel review lanes, aggregate verification
and one GBNF-guided CPU model inference. Model checksum was verified; the
report recorded `model_executed=true`, `story_contract_passed=true`,
5.089 seconds elapsed and 544,292 KiB peak child RSS. The model produced
a parseable JSON object with exactly four beats.

However, inspection of the archived text shows generic repeated navigation
actions and **no accomplished repair** in the supposed payoff. The story
did not meet the prompt's 25–60-word-per-beat instruction. This is a
**manual editorial failure**, even though the old 15–140-word automated
length contract passed. Output is unapproved, unready, unpublished.

The revised minimum automatic draft screen now matches the prompt's
25–60 word beat range; a regression test reproduces and rejects the exact
bad four-beat artifact. Longer beats alone would not establish causal
fidelity or originality: manual review remains mandatory, no production
promotion is permitted. This change is a validator correction only;
**no fourth real model inference is authorized or run**.

## Review-only causal negative controls after run #41660334335

The real GBNF output achieved valid JSON structure but not meaningful
story completion. A new **experimental lighthouse-only** deterministic
negative-control audit now looks for an observable physical attempt,
a consequential obstacle, a completed repair action and the warning
signal visibly working in the payoff. It also flags repeated generic
navigation instead of progress. Unknown profiles fail closed.

The audit is explicitly **not semantic understanding**: keyword cues can
miss good prose or be fooled by bad prose. It can reject a weak draft
but cannot approve one. Only candidates passing both the 25–60-word
four-beat structure contract and conservative causal cues get a
review-only candidate JSON. Everything still needs human editorial and
visual review; production-ready, approved and published remain false.

The stronger prompt and new rejection tests do not authorize another
real model benchmark. ASTRA Main, publication gates, paid services, and
existing animation/story workflows are unchanged.

## Planned four-stage causal comparison (next experimental trial)

The baseline real GBNF run #41660334335 produced structurally valid but
unresolved story text. Repeating the identical freeform prompt would not test
a meaningful hypothesis. The next single comparison supplies a **fixed,
review-only four-step causal plan** to the same pinned Qwen 0.5B model:
problem, attempted fix, lightning setback, completed repair and visible
beacon outcome.

The plan is data, not an external API or an assertion that the model followed
it. The model must expand it to four 25–60-word beats without inventing
a different conclusion. Inference outputs continue through both the structure
contract and conservative lighthouse-specific negative controls.
Any passing automated result remains `semantic_quality=not_verified`,
`approved=false`, `production_ready=false`, and `published=false`.
The plan digest in the report records exactly what guidance was supplied.
Manual review is still required to compare actual causal fidelity.

To prevent incidental retries, the single coordinated workflow requires
the *new exact one-shot commit message*
`experiment(ASTRA): planned GBNF one-shot CPU validation` on its isolated
branch, after the three parallel lightweight lanes and aggregate pass.
Ordinary commits and PR checks do not run model inference. The legacy
standalone manual benchmark remains separate.
