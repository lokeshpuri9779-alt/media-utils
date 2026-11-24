# ASTRA GitHub-native multi-format Shorts pipeline

ASTRA's caption-only production path now runs on GitHub-hosted Actions. It produces narration + synchronized captions only: no animation, illustrations, stock footage, or music.

## One-click local story generation and rendering

1. Open the repository's **Actions** tab.
2. Select **ASTRA Local Story to Caption Short**.
3. Click **Run workflow** and choose a content direction: fiction, facts, science, history/geography/GK, myth-vs-fact, puzzles, riddles, quizzes, psychology, business, technology, current news, or trending topics.
4. Wait for the runner to generate a story, apply quality gates, synthesize narration, render captions, and decode-check the MP4.
5. Download the `rayvan-local-story-short-<run id>` artifact from the completed run.

No local computer, WSL2, Gemini key, vidIQ credits, hosted inference API, or external paid AI API is used for generation. The Qwen3-4B Q4_K_M model is downloaded from its public model repository and runs locally on the GitHub Actions CPU runner. Its model card lists Apache-2.0 licensing and a 2.5 GB quantized model. The first run downloads the model; subsequent runs may restore it from GitHub Actions cache.

## What the local story engine does

- Generates a seven-beat short-form script adapted to the selected content direction.
- Requires a 65–85 word complete spoken script, including a format-specific audience question.
- Rejects wrong beat order, weak length, generic CTAs, repeated lines, selected cliché endings, and topics too similar to recent ASTRA content.
- Saves only title, premise, and fingerprint in `data/story_history.jsonl` to help prevent repeated plots.
- Passes the candidate into the existing Kokoro narration + timed-caption renderer.
- Leaves approval and publishing false. The output is a review artifact only.

## Content directions

- **Fiction:** surprise, mystery, sci-fi, emotional, thriller, moral dilemma.
- **Facts and explainers:** weird facts, science explained, history GK, geography GK, world GK, myth vs fact, psychology, money/business, technology explained.
- **Interactive:** brain puzzles, logic puzzles, riddles, three-question quick quizzes.
- **Timely:** current news and trending topics, with an RSS source pack collected at run time from Google News India and Google Trends India.

Puzzles are structured to give viewers a chance to think before the reveal. Quizzes should give clear answers and short explanations. Facts and GK are still AI-generated drafts: automated word-count and structure checks do **not** prove factual accuracy. Human verification is required before approval.

For **current news** and **trending topics**, the workflow retrieves RSS headlines and links before generation, passes those items to the model, and stores them in `candidate.json` and `sources.json`. RSS headlines are leads, not independent fact-checking. The script must not invent dates, statistics, or outcomes, and a human must open the source links and verify claims before publishing. If the feeds fail or return too few sources, that run stops rather than inventing a news script.

## Outputs

- `candidate.json` — generated story candidate
- `rayvan-short.mp4` — narration with static, timed captions
- `rayvan-short.captions.json` — phrase timing manifest
- `rayvan-short.review.json` — review report

## Boundaries and honest limitations

- This is local model inference **on GitHub's runner**, not an external hosted AI API. Model weights are downloaded from Hugging Face; source code, orchestration, execution, history, and output artifacts are managed through GitHub.
- The 4B model is a small CPU-friendly starting point, not a frontier writing model. Passing automated checks does not prove a story will perform well. We need actual audience retention and engagement data to calibrate it.
- The first run may take longer because the model and Python runtime are installed. Runner CPU time and artifact/cache quotas apply.
- Workflow is manual-only. No daily schedule is enabled, and no YouTube upload or publishing occurs.
- The story history commit requires the workflow's repository write permission. If branch protection blocks the bot push, the generation step may complete but persistence of history will fail.
- The separate **ASTRA Caption-only Render** workflow remains available for rendering an existing candidate under `queue/pending/`.

## Test the story validator

The fast, model-free checks run in the existing **ASTRA Performance Shorts Contract** workflow when the generator or tests change:
`python -m unittest tests.test_github_local_story_generator -v`.
