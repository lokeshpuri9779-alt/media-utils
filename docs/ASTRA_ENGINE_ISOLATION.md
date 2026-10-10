# ASTRA production/experimental isolation policy

ASTRA Main is the protected production video engine. The Blender/Cycles tools in this repository are **experimental** until explicitly promoted.

## Boundaries
- Experimental benchmarks are manually dispatched; they do not upload videos or access YouTube credentials.
- No benchmark may trigger or modify ASTRA Main workflows, publishing schedules, secrets, or OAuth tokens.
- A successful timing benchmark is not sufficient for production promotion.
- Changes require rendering, visual quality, reliability, resource-cost, and regression evidence, plus an explicit promotion decision.
- Preserve a known-working version and a rollback procedure before integration.
- If benchmark measurements are missing or invalid, the experimental renderer selector defaults to Eevee; this does not imply the production engine currently uses Eevee.

## Promotion evidence
Record commit SHA, hardware, Blender version, frame count, render samples, resolution, median and worst-frame duration, peak memory where available, visual review, failure rate, and comparison to the existing production output.

## Current status
Cycles benchmark and budget router are prototypes. Neither is verified to be integrated with ASTRA Main. Do not describe ASTRA Main as verified running without checking production logs.
