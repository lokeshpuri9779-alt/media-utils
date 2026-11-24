# Performance Shorts editorial queue

This branch stores review-only candidate data separately from the production code on `main`.

## Queue

- `performance_short_review_queue.json` is the durable editorial inbox.
- Only seven-scene packets with `format_profile=shorts_v2_7scene` are accepted.
- Every candidate must remain `approved=false`, `production_ready=false`, `eligible_for_automatic_publishing=false`, and `published=false`.
- `approved_count`, `rendering_triggered`, and `publication_triggered` remain zero/false.
- Re-importing the same candidate ID and SHA-256 is idempotent. Reusing an ID with different source content is rejected.
- A malformed queue is not overwritten; recover it manually from Git history.

## Local intake

From a checked-out working copy of the code repository, produce a review packet using the existing review-packet builder, then run:

```bash
python -m astra_v2.performance_short_intake \
  --packet path/to/performance-short-packet.json \
  --queue performance_short_review_queue.json
```

Review the resulting JSON and commit it to this branch explicitly. Do not connect this queue to render, scheduling, or publishing automation.

## Current status

The queue is initialized and empty. No candidate has been generated, imported, or approved.
