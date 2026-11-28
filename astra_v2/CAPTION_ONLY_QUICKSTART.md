# ASTRA GitHub-native multi-format Shorts pipeline

ASTRA's caption-only path runs on GitHub-hosted Actions. The cinematic renderer produces full-screen 9:16 moving visuals with subtle, phrase-synchronized floating captions and narration. It is not a static caption card or permanent lower-third. Gemini-backed fiction generation is an optional lane; the local Qwen path remains available and is not replaced.

## Workflows

- **ASTRA Parallel Caption Shorts Batch** — manually starts a nine-lane review batch: brain puzzle, science, India GK, money/business, mystery, geography, psychology, what-if, and trending topics. Up to four lane jobs may run concurrently after a shared cache-preparation job.
- **ASTRA Single-Lane Diagnostic** — manually tests one lane end-to-end without writing story history or publishing.
- **ASTRA Local Story to Caption Short** — manually generates one selected direction and renders a review artifact.
- **ASTRA Caption-only Render** — renders an existing review candidate from `queue/pending/`.
- **ASTRA Caption Short Generate + Review Render** — manually generates one Gemini-backed seven-scene fiction candidate, renders the cinematic caption-only MP4, and uploads a review-only artifact. It requires `GEMINI_API_KEY` and does not publish.

The caption inference workflows share one concurrency group to prevent overlapping model runs and competing writes to the shared originality history. Generation and rendering commands have hard time limits. A timeout fails the run safely; it does not trigger publishing.

## Generation and validation

The pinned Qwen3-4B Q4_K_M model remains available locally on the GitHub Actions CPU runner for its multi-format generation path. The separate fiction workflow uses the configured Gemini model when `GEMINI_API_KEY` is present; Gemini is retained rather than replaced. Neither route grants production approval or publishing permission.

The generator adapts structure to the content direction:
- Puzzles use challenge, thinking pause, answer, and explanation.
- Facts and explainers use curiosity hook, surprising fact, explanation, and why it matters.
- Quizzes use quiz hook, question/options, answer reveal, and explanation.
- News uses news hook, what changed, context, and why it matters.
- Original fiction uses a seven-beat story arc.

The complete spoken script is constrained to 65–85 words, including a specific audience question. Compact four-beat scenes allow 10–18 words each, with the prompt aiming for 14–16 words. Validation rejects incorrect role order, weak length, generic CTAs, repeated lines, selected cliché endings, and topics too similar to recent ASTRA content. Validation does not prove factual accuracy, originality in the legal sense, or audience performance.

Candidates are explicitly marked `approved: false`, `production_ready: false`, and `published: false`. The renderer refuses candidates without those explicit review-only flags and validates the expected scene-role sequence.

## Human-authorized render of a generated fiction candidate

After the review-generation workflow has been merged to the default branch and run successfully, use **ASTRA Approved Caption Short Review Render** with the exact generation run ID and candidate ID from its artifact. Inspect the candidate and review packet first. Choose `approve_for_review_render` only after that inspection and provide a meaningful reviewer attestation; choose `reject` to record rejection without rendering.

The workflow downloads the artifact from that exact run, verifies the candidate identity and SHA-256 against both the review packet and one-item review queue, and checks that all approval/publication flags remain false. Only then does it render the caption-only MP4 and upload a review artifact. The dispatch actor, decision, attestation, source run and candidate hash are recorded in a decision receipt. This is permission to create a review render only; it does not approve production, commit to `queue/pending/`, schedule, upload to YouTube or publish. Production editorial approval and all existing publisher gates remain separate.

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
