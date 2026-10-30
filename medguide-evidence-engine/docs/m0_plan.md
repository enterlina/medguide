# M0 plan, inventory, and risks

## Existing workspace inventory

- Next.js 16.3.4 / React 19.2.8 prototype under the workspace root.
- Routes: dashboard, medications, schedule, interactions, history, clinical trials, clinical trial
  mode, coordinator dashboard, and settings.
- UI/data modules live in `components/`, `data/`, and `types/`.
- No pre-existing backend, database schema, Python package, or evidence ingestion code.
- No `.git` directory is present, so commits cannot be created from this workspace copy.

## M0/M1 plan

1. Add an isolated `medguide-evidence-engine/` Python package.
2. Define strict source and normalized-record models plus storage/client protocols.
3. Commit a fixed offline seed manifest and compact official-source-derived fixtures.
4. Persist append-only snapshots and canonical identifiers in SQLite.
5. Validate caps, idempotency, provenance, exact-ID linking, and update history offline.

## Risks and controls

- **Scientific overclaiming:** M1 stores source metadata only and performs no synthesis.
- **Publication/registration double counting:** entities remain separate and are linked by exact IDs.
- **Silent source changes:** SHA-256 changes create a superseding immutable snapshot.
- **Rights ambiguity:** access/license metadata is explicit; no publisher content is scraped.
- **Prototype regression:** the Next.js app and its configuration are not modified.
- **SQLite scale:** accepted for the small seed; storage remains behind an interface for migration.
- **Fixture staleness:** retrieval and source-update timestamps are recorded and visible.

