# P0 incident: long-form queue head starves Shorts during cooldown

**Observed:** 2026-10-11 13:16 IST. **Status:** production fix BLOCKED by repository write safety; not deployed. **Owner:** ASTRA reliability director (creative/thumbnail experiments remain separate).

## Verified evidence
- GitHub publisher runs 38120376308, 38121308446, 38121588016 and 38122412994 completed green but each reported `ASTRA_V2_RESULT.outcome=skipped`, `reason=longform_24h_cooldown`. Runs repeatedly selected `ASTRA_PRELOAD_CONSUMED=trend-brief-2026-10-11-am` rather than a Short.
- The 2026-10-11 07:45 UTC publisher log shows `attempts_today=37`, `confirmed_today=37`, `pending=0`; a successful workflow is not evidence of a fresh upload.
- The 07:29 UTC preloader reports `ASTRA_QUEUE_COUNTS={"target":24,"usable":24,"artifacts":117}` and `buffer_full` for lane zero, despite the publisher being blocked by an ineligible long-form artifact.
- Last recorded long video in `astra-state/performance.json`: `eAp_chXg1rA` at 2026-10-11T00:15:17+05:30; next long upload must wait at least 24 hours and pass creative QA.

## Root cause
`astra_v2/run.py` calls `astra_v2.preload_queue.take()` before evaluating long-form eligibility. `take()` returns the oldest valid artifact without format filtering. The publisher then rejects the long artifact for cooldown, skipping the entire upload opportunity instead of selecting an eligible Short. The existing `astra_v2/long_cadence.py` durable historical guard is not called by `run.py`; the latter uses a journal-only local guard.

## Reversible fix proposal (NOT DEPLOYED)
1. Add an optional backward-compatible `allow_long=True` parameter to `preload_queue.take`; after validating candidate metadata and before loading MP4 bytes, skip artifacts with `format=long` when `allow_long=False`. Reject unknown formats.
2. In `run.py`, compute long eligibility using `astra_v2.long_cadence.long_upload_due(state, utcnow(), performance=read_json('performance.json'))` and pass it to `take(..., allow_long=long_due)`.
3. When long is cooling, never invoke the on-demand `make_long_candidate` fallback; try approved Shorts. Recheck the historical guard immediately before any long upload.
4. Preserve unresolved long reservations and pending transfers as fail-closed blockers. Do not delete artifacts or reservations, change OAuth, or alter upload quotas.
5. Add tests: historical long upload blocks after journal reset; pending/reserved long blocks indefinitely pending review; queued long is skipped while eligible Short is selected; long resumes after >=24h; duplicate ID, title, source and media QA remain enforced.

## Validation, expected KPI, rollback
**Observed production validation:** multiple independent logs prove queue starvation; proposed fix was not applied because the GitHub production-code update was rejected by safety checks. **Expected KPI:** publisher stops returning repeated `longform_24h_cooldown` for eligible Shorts, while long-form interval remains >=24h. **Acceptance:** tests pass and two consecutive production publisher runs show Shorts selection or a meaningful independent quality/quota reason, without duplicate/publication errors. **Rollback:** revert only the future queue and publisher commits; keep durable history, credentials and state untouched.

**Do not mistake a green workflow, this documentation commit, or a local prototype for a deployed production fix.**
