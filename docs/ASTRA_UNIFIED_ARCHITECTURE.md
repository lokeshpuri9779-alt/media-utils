# ASTRA — one integrated adaptive preproduction architecture

## Structural choice

Prefer **composition + strategy injection** over parallel inheritance trees.
Each worker implements one interface and consumes/produces immutable content-addressed
artifacts. The dependency graph determines what can run concurrently and what
must be rebuilt. Use visitors only for cross-cutting operations over genuinely
stable heterogeneous domain models; collapse redundant hierarchies.

- Planning: forecast supply, demand, resource and storage constraints.
- Creation: story, characters, scenes, voice, audio, subtitles and metadata.
- Validation: provenance, editorial approval, copyright, policy, QA, uniqueness.
- Warehouse: immutable artifacts, versioned manifests, dependency hashes, retention.
- Scheduling: bounded parallel workers, dynamic priority, retry/backoff, checkpoints.
- Publishing: transactional lease, idempotency, history reconciliation, upload proof.
- Learning: collect outcome metrics, evaluate experiments, update future strategy.

**One integration effort, many parallel components:** all modules target the same
manifest schema, inventory state machine and safety contract. No independent
competing publishing engines.

## OmniRoute second opinion

Treat OmniRoute as an injected independent reviewer for architecture decisions,
story/asset plans, resource policies and process changes. Review both the proposal
and the reasoning/evidence used to produce it. Store model/provider/version,
timestamp, prompt digest, response digest, verdict and disagreement rationale.
Never claim an OmniRoute review occurred unless an actual response was received.

A local gateway is not a verified free inference provider. Do not invoke unknown-
cost providers, and do not accept post-request cost checks as a spending guarantee.
If no verified zero-cost reviewer is available, record unavailable; keep the
second-opinion-dependent decision unapproved rather than inventing consent.
This second opinion supplements, never replaces, human editorial approval.

## Production deployment prerequisites

1. Transactional shared store with atomic leases, CAS and crash recovery.
2. Durable object storage, immutable hashes, retention and restore tests.
3. Existing real editorial manifest validator integrated at registration.
4. Producer adapters for every media type with dependency-aware QA.
5. Pre-rendered YouTube queue and live API confirmation.
6. Verified free OmniRoute provider and cost/rights benchmark.
7. Observability, adaptive feedback, reproducible tests and soak checks.

Until these are implemented, the new modules are **offline contracts only**.
The current publisher stays unchanged; no bypasses or paid inference.
