# ASTRA GitHub-native multi-format Shorts pipeline

ASTRA's caption-only path runs on GitHub-hosted Actions. It produces narration plus phrase-synchronized captions on a solid background: no animation, illustrations, stock footage, B-roll, music, branding overlays, or CTA overlays.

## Workflows

- **ASTRA Parallel Caption Shorts Batch** — manually starts a nine-lane review batch: brain puzzle, science, India GK, money/business, mystery, geography, psychology, what-if, and trending topics. Up to four lane jobs may run concurrently after a shared cache-preparation job.
- **ASTRA Single-Lane Diagnostic** — manually tests one lane end-to-end without writing story history or publishing.
- **ASTRA Local Story to Caption Short** — manually generates one selected direction and renders a review artifact.
- **ASTRA Caption-only Render** — renders an existing review candidate from `queue/pending/`.
- **ASTRA Caption Short Review Generation** — manually generates exactly one seven-scene fiction candidate with the configured Gemini model and stores a candidate, review packet, and one-item review queue as a 14-day artifact. It requires the repository secret `GEMINI_API_KEY`; optionally set repository variable `ASTRA_GEMINI_MODEL`. It does not render or publish and does not write to the repository's persistent queue.

The caption inference workflows share one concurrency group to prevent overlapping model runs and competing writes to the shared originality history. Generation and rendering commands have hard time limits. A timeout fails the run safely; it does not trigger publishing.

## Generation and validation

The pinned Qwen3-4B Q4_K_M model runs locally on the GitHub Actions CPU runner. No paid inference API, Gemini, vidIQ credits, local computer, WSL2, or external paid AI service is required.

The generator adapts structure to the content direction:
- Puzzles use challenge, thinking pause, answer, and explanation.
- Facts and explainers use curiosity hook, surprising fact, explanation, and why it matters.
- Quizzes use quiz hook, question/options, answer reveal, and explanation.
- News uses news hook, what changed, context, and why it matters.
- Original fiction uses a seven-beat story arc.

The complete spoken script is constrained to 65–85 words, including a specific audience question. Compact four-beat scenes allow 10–18 words each, with the prompt aiming for 14–16 words. Validation rejects incorrect role order, weak length, generic CTAs, repeated lines, selected cliché endings, and topics too similar to recent ASTRA content. Validation does not prove factual accuracy, originality in the legal sense, or audience performance.

Candidates are explicitly marked `approved: false`, `production_ready: false`, and `published: false`. The renderer refuses candidates without those explicit review-only flags and validates the expected scene-role sequence.

## Seven-scene fiction review generation

The separate **ASTRA Caption Short Review Generation** workflow is an optional Gemini-backed fiction lane, not a replacement for the local Qwen multi-format pipeline above. It is manually triggered, generates exactly one candidate per run, and has a 12-minute job limit. A missing Gemini secret fails before generation. The workflow verifies all candidate, packet, and queue promotion flags remain false, then uploads the JSON review artifacts for 14 days. It does not commit candidates to `queue/pending/`, render an MP4, change approval state, or invoke the YouTube publisher. A human must inspect the candidate and decide whether to place a selected candidate into the existing caption-only render process.

## Factual and timely content

Facts and GK remain AI-generated drafts. Human verification is required before approval. Current news and trending topics use RSS headlines as leads; they are not independent fact-checking. The source links must be opened and claims verified before publishing. If feeds fail or return too few usable sources, the run stops rather than inventing a news script.

## Review artifacts

- `candidate.json` — generated story candidate
- `rayvan-short.mp4` — narration with synchronized captions
- `rayvan-short.captions.json` — phrase timing manifest
- `rayvan-short.review.json` — review report
- `sources.json` — source leads for news/trending lanes

The output is for human review only. No workflow in this caption-only path uploads or publishes to YouTube. The separate YouTube publisher is a different, manually invoked workflow and is not part of this pipeline.

## Known limitations

- The 4B model is a practical CPU-runner starting point, not a frontier writing model.
- A green contract-test workflow proves software contracts, not that the model will produce a strong story on every attempt.
- Audio duration is checked after synthesis; a script can pass text validation and still fail the render-duration gate.
- GitHub runner capacity, cache quotas, artifact retention, and model download times can affect throughput.
- Actual audience performance must be calibrated from retention and engagement data after reviewed videos are published by an authorized operator.
