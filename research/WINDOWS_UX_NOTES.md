# Windows UX Notes — Interactive Blueprint Dashboard (Future Direction)

**Placeholder:** ACT-028 (NOT Week 2 scope)
**Owner:** Tnsr-Q
**Status:** captured; deferred

## Context

Current blueprint deliverables are static PNG renders (`visualization prototype.png`,
`visualization-with-fixes.png`). Every contract revision forces a manual image
re-render → drift risk between image and `openapi/openapi.yaml`.

## Intent

The user's eventual goal is to make the blueprint **"windows usable"** — i.e.
an interactive web dashboard driven directly from `openapi/openapi.yaml`, not
a regenerated image artifact.

## Sketch (non-binding, future)

- **Single source:** read `openapi/openapi.yaml` at build time (or runtime) and
  derive the panel graph from `paths`, `tags`, `components.securitySchemes`.
- **Rendering stack candidates:** React + ReactFlow / Cytoscape / D3, with the
  same blueprint aesthetic (dark grid, cyan accents) as a CSS theme rather
  than a baked image.
- **Auto-sync panels:**
  1. User & Order Management → `/users`, `/orders`
  2. Circuit Creation → `/circuits/*`
  3. Quantum Compute Jobs → `/quantum/jobs/*`
  4. Smart Guidance → `/guidance/assist`
  5. Encryption & Decryption → `/security/*`
  6. Security & Performance Monitoring → `/monitoring/*`, `/dashboard/metrics`
  7. Update Orchestration → `/updates/*`
  8. AGI Self-Improvement → `/agi/self-improvement/runs`
  9. Training Jobs, Analytics, Notifications → `/training/*`, `/notifications`
- **Live validation badges:** run `scripts/validate-openapi.sh` in CI and render
  the pass/warn status into the dashboard header.
- **Clickable endpoints:** link each node to the Redoc/Swagger view of that
  path for inline docs.
- **Freeze-hash ribbon:** once ACT-019 lands, surface the canonical freeze hash
  of each circuit / training job next to its node so the UI doubles as a
  reproducibility ledger.

## Why not now

- Week 2 priorities are correctness of the contract (ACT-019 freeze hashing,
  ACT-020 plugin registry, ACT-021 routing policy).
- A dashboard without the underlying deterministic primitives would just be
  another stale image, in HTML clothing.

## Trigger to promote to a real ACT

When (a) freeze hashing is live and (b) plugin registry descriptors exist,
the dashboard stops being cosmetic and starts being load-bearing. At that
point, open **ACT-028: Interactive Blueprint Dashboard** with a concrete
spec.

---
*Captured 2026-04-22 during ACT-019 kickoff. No implementation here — forward
pointer only.*
