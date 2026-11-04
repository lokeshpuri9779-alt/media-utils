# ASTRA source-masked offline story review — v1

This experiment adds a **human-scored, source-masked review packet**, not
a model quality score or ASTRA production lane.

## What the packet compares

One lighthouse theme with three story texts:
- The 0.5B Qwen output captured in regression fixture for
  [real CPU run #41660334335](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41660334335).
- The 1.5B Qwen output captured in regression fixture for
  [real CPU run #41707761872](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41707761872).
- A new assistant-drafted lighthouse reflector-repair reference, with a
  declarative event-state ledger. It was written **after** inspecting
  the previous model failures; it is **not** an independently verified
  human-authored gold standard.

These samples **were not generated using matched prompts, equal output
length constraints or a preregistered study design**. They cannot provide
a statistically valid model comparison. The packet hides explicit source
labels, but it is not a true double-blind study (the repository and
provenance can be inspected, and writing style may reveal origins).

## What is created

Run the existing story lane of `astra-offline-ai-parallel.yml`.
It generates two separate GitHub artifacts:

1. `astra-offline-blind-review`:
   `blind-review.json` and `rating-template.json` with three stable,
   source-agnostic review IDs. No prefilled numerical quality ratings.
2. `astra-offline-blind-source-key`: `source-key.json`, with the matching
   model and run provenance, to consult **only after** scoring.

The earlier `astra-offline-story-reference` packet still exists for
distinct-genre baseline story inspection. All generated material lives
under `artifacts/`, not in ASTRA Main or publishing.

## Human-review instructions

Read the source-masked review packet before opening the key. For **every**
story, score five dimensions on a 1–5 scale: cause/effect, visible
physical action, payoff resolution, novelty/detail, and renderability.
Add concrete text-based evidence for every dimension, ideally identifying
both strengths and failures. There is no 'automatic passing score'.

Fill `rating-template.json` with the reviewer label and one integer
score plus a 12–500 character explanation for each dimension. Then run:

```bash
python3 -m tools.astra_offline_blind_review \
  --output-dir artifacts/offline-blind-story-review \
  --ratings path/to/completed-human-ratings.json
```

Only an exact set of three unique IDs, a matching packet hash, scores
in 1–5, and bounded evidence are accepted. Invalid/partial forms fail
closed. `review-scores.json` is generated only with **supplied ratings**,
not by automatic content scoring. Human identity cannot be verified.

The resulting summary is a **descriptive input to future research**,
not production approval. Every artifact and score report keeps
`approved=false`, `production_ready=false`, `published=false`.
No downloads of model weights, inference, API calls, scheduling, GitHub
merge, approval routing or YouTube publishing are part of this task.

## Interpretation

Separating source labels helps reduce immediate anchoring, but it cannot
repair sampling bias, post-hoc references, prompt differences, or very
small sample sizes. Do **not** make claims that a given model is superior
or that the assistant-drafted reference meets professional publishing
quality from this comparison alone. Further work should use independently
selected prompts, matched settings, blind human scoring, multiple topics,
and a separate protected publishing gate.
