# Fixed-noise prompt intervention review

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40579389683

Code: `7321589f9f4bdd720098a518875329961791f5ea`. Artifact `12768523756` expires 2026-11-03 20:42 UTC. Workflow succeeded; the original PNG was visually inspected.

## Controlled comparison

Baseline: run 40537578850, OpenVINO image. Model revision, 512x512 resolution, 20 steps, guidance 7.5, FP32, core package versions and scheduler settings match. Scheduler provenance list order was normalized for comparison. The downloaded initial tensor hash matches the baseline exactly:

`e97f3de04c7c6ba86354db4402b91d4402ede9c72aabed29a96dd7d635a798ba`

Positive prompt: A single red toy fire engine, side view, one complete vehicle with attached wheels and ladder, fully visible, centered on a plain white studio background.

Negative prompt: multiple vehicles, duplicate, detached parts, disassembled, collage, text, letters, watermark, colored background, people

The two prompts changed together. This measures their combined effect, not the independent contribution of positive versus negative wording.

## Manual visual review

Partial improvement: one dominant red toy vehicle replaces the baseline's multiple vehicles and detached ladder/wheel-like object. It is fully visible with margin and has no obvious people.

Overall semantic result: FAIL. The vehicle has distorted, ambiguous geometry and is not convincingly a fire engine with the requested attached ladder. A tall rectangular frame is not a clearly identifiable ladder. The view is oblique rather than a strict side view. There is a logo/text-like mark on its front despite the negative prompt. The background and floor are blue-gray, not plain white.

The machine pixel-quality check passes. That does not override the manual semantic failure. Character continuity was not tested.

Verified PNG SHA-256: `7e27d5f038d1ded5b5e0a0df1805d02b3e6a0e4fab5968a51624ee1ce195584f`

Setup: 92.30 s. Inference: 209.66 s. Worker elapsed: 302.09 s. Peak RSS: 12,567,500 KiB. These are single-run observations.

## Decision

The tested SD1.5 CPU configuration remains unsuitable as a reliable ASTRA image path. Prompt changes improved object count but did not establish object identity, coherent detail, background fidelity or freedom from text-like marks. The prior native PyTorch/OpenVINO comparison reproduced the same baseline failures, so backend conversion remains a weak explanation for that case.

Stop the conditional seed-123 run and further step/seed sweeps for this prompt pair: the first-image semantic prerequisite failed. Combined-scene and character-continuity validation remain blocked.

The next useful validation requires a deliberate candidate change rather than a larger sweep: select one alternative model only after checking license, CPU support and memory fit; then run one bounded, review-only image against the same explicit object rubric. A successful single image would only justify a second seed and scene validation, never automatic approval. No new model is selected or downloaded by this review.

Keep approved=false, production_ready=false, published=false, manual_visual_review_required=true. No automatic approval, production fallback, paid APIs, publishing or main-branch integration was enabled.
