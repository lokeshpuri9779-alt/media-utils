# ASTRA pending story candidates

Place one review-only story candidate JSON file in this directory, then run the
**ASTRA Caption-only Render** GitHub Actions workflow manually.

The workflow accepts only paths inside `queue/pending/`. The candidate must
contain exactly seven `performance_scenes` in this order:

1. `hook`
2. `stakes`
3. `attempt`
4. `setback`
5. `discovery`
6. `climax`
7. `payoff`

Every scene needs non-empty `speech`, and the root object needs a
story-specific `question` for the spoken engagement prompt.

Candidates must remain unapproved and unpublished. The workflow produces a
review-only MP4, caption timing manifest, and review JSON as a GitHub Actions
artifact. It does not publish to YouTube.

This folder is an intake queue, not an AI story generator. Story generation
will be connected as a separate GitHub-hosted stage after its model and
cost/usage limits are selected.
