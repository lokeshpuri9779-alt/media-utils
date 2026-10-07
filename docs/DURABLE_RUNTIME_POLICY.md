# Astra Durable Runtime Policy

Astra is designed to survive model/provider churn rather than preserve one renderer.

## Invariants
- Creative identity, continuity state, quality metrics and render manifests are portable.
- Renderers implement a versioned capability contract and are replaceable adapters.
- Discovery never authorizes production.
- A candidate must pass health/capability checks and quality canaries before activation.
- Active renderers are degraded or quarantined automatically after health/quality regression.
- Retired renderers never auto-return.
- Capacity loss queues/checkpoints work; it does not silently substitute lower quality.
- Paid inference always requires explicit user approval.
- Public release remains behind Astra's quality gate.

## Lifecycle
discovered -> canary -> active
active -> degraded/quarantined
degraded/quarantined -> canary after recovery
retired -> retired

This policy intentionally does not restore previously removed Wan, LTX or Agnes integrations.
