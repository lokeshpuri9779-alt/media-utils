# ASTRA Adaptive Warehouse — unified implementation contract

ASTRA must preprocess and store stories, approved decisions, character/scene assets,
voice, captions, sound, renders, thumbnails, metadata, QA and publication packages.
Workers should independently replenish inventory according to measured demand,
lead times, provider availability and storage. Publishing must consume only
previously rendered, validated and approved packages.

## Non-negotiable boundaries

- No automatic invention of editorial approvals; use existing hash-bound intake.
- No unverified-cost provider calls, unlicensed assets or uncontrolled spending.
- No duplicate uploads; preserve publisher history and YouTube reconciliation.
- Never mistake green workflow status for a confirmed published video.
- Never delete or overwrite existing production history during migration.

## Pilot module

`astra_v2/adaptive_warehouse.py` implements a persisted artifact-state contract,
integrity checks, QA gating, immutable content identities and an adaptive reserve
formula. This is **not** yet wired into the live publisher.

**Concurrency limitation:** JSON replace is atomic for a single writer only.
Before multiple GitHub Actions workers share this queue, migrate state transitions
and reservations to a transactional, durable store with atomic compare-and-swap,
leases, crash recovery and publication reconciliation. A local JSON file or
ephemeral GitHub Actions artifact must never be treated as a multi-run queue.

## Integration requirements

The optional shared implementation is documented in
[ASTRA_SHARED_WAREHOUSE.md](ASTRA_SHARED_WAREHOUSE.md): PostgreSQL receipt indexing,
atomic claims, server-clock leases and idempotent confirmations. It is separate
from this JSON pilot and is not configured as the live publisher's backend.

1. Bind approved-story manifest hashes and real review evidence at intake.
2. Store immutable artifacts in persistent storage with retention and checksums.
3. Run independent asset, TTS, render, metadata and QA workers ahead of publication.
4. Introduce transactional reservations and idempotent YouTube upload confirmation.
5. Run capacity/rights/provider tests, backfills and dry runs before enabling.
6. Calibrate adaptive targets with production metrics and bounded experimentation.
7. Preserve existing live publisher until end-to-end verification succeeds.
