# ASTRA immutable artifact storage

`ArtifactStore` persists bytes under SHA-256 content addresses, deduplicates
identical media, and verifies integrity before use. It is a **local storage
adapter**, not a hosted warehouse. It does not create approval, accept a
publishing decision, or invoke providers.

The existing GitHub Actions preload package already carries a video digest
and performs its own QA. The new store can ingest such packages in an isolated
worker once a verified persistent storage backend is selected.

## Production gap

GitHub-hosted runners do not share local directories. Actions artifacts expire
and cannot be relied upon for unlimited long-term inventory. A remote object
store and transactional queue are required for independent workers. Validate
retention, commercial terms, upload/download costs, credentials, backups and
restore tests before migration. Keep the current publisher unchanged until
the new path demonstrates verified upload and reconciliation.
