# Action Manifest — Katopu API Modernization (Week 1 Execution Focus)

## Executive Summary

Contract-first modernization is complete for core API design (idempotency, pagination, webhook signature contract, security defaults). Week 1 now focuses on converting contract confidence into operational confidence with pragmatic, high-ROI steps.

OpenMythos guidance remains active as a standing rule for decisions:
- adopt plugin architecture for optimization strategies,
- use documentation patterns that include actionable client examples,
- enforce CI validation for spec evolution.

## Week 1 Immediate Priorities (Now)

| Action ID | Priority | Action | Week 1 Deliverable | Acceptance Criteria (Falsifiable) | Dependencies |
|---|---|---|---|---|---|
| ACT-013 | P0 | Re-prioritize manifest around runtime readiness | Updated manifest with execution-ready sequence | This file contains explicit Week 1 actions with owner-ready acceptance criteria | None |
| ACT-014 | P0 | Decide training compute strategy (provider + budget) | `docs/training-compute-strategy.md` | Doc contains provider decision, monthly budget envelope, phase gates, and rollback trigger | ACT-013 |
| ACT-015 | P0 | Validate SHA-256 verifier against realistic webhook payloads | Automated test script + fixtures + recorded run output | Plugin returns VERIFIED for valid signatures and INVALID for tampered signatures across both webhook event types | ACT-013 |
| ACT-016 | P1 | Add CI contract-validation pattern (OpenMythos-inspired) | Planned in next iteration (workflow + checks) | CI job fails on OpenAPI validation/test failures | ACT-013 |
| ACT-017 | P1 | Plugin architecture expansion for circuit optimization strategies | Spec draft for plugin contract | `plugins/` includes clear plugin contract for non-security plugins | ACT-015 |
| ACT-018 | P2 | API client example structure alignment | Structured docs/examples for common API flows | `docs/` includes executable-style request/response examples for key endpoints | ACT-013 |

## Remaining Backlog Reprioritized

| Priority | Area | Why It Matters Now | Suggested Timing |
|---|---|---|---|
| P0 | Runtime webhook verification enforcement | Prevents spoofed callbacks in production | Week 1-2 |
| P0 | Training compute provisioning strategy | Unblocks real training execution beyond contract-only API | Week 1 |
| P1 | Idempotency persistence in runtime store | Prevents duplicate side effects under retries | Week 2 |
| P1 | Cursor determinism at persistence layer | Ensures stable list behavior under load | Week 2 |
| P1 | CI policy for OpenAPI/spec evolution | Prevents regression drift | Week 2 |
| P2 | Full capability matrix (contract vs implemented) | Improves release clarity and onboarding | Week 3 |

## Dependency Graph (Week 1)

1. **ACT-013** (manifest reset)
2. **ACT-014 + ACT-015** (parallelizable execution)
3. **ACT-016 + ACT-017** (next iteration, based on Week 1 outcomes)
4. **ACT-018** (docs maturity once runtime direction is stable)

## Risk Notes

- Largest delivery risk is not API contract quality; it is runtime infrastructure readiness.
- Compute cost can drift quickly without strict budget caps and phase gates.
- Signature verification is robust only when raw-body hashing is preserved end-to-end.

## Rollback Strategy

- Keep all Week 1 work in isolated commits by action ID.
- If operational tests fail:
  1. keep contract-level spec changes,
  2. disable non-critical runtime extensions,
  3. rerun deterministic plugin tests before re-enabling.


## Research-Informed Actions (Post-Week 1, Not Immediate)

> **Status:** Research Phase — Not Week 1 execution scope.

| Action ID | Phase | Priority | Action | Why It Matters | Acceptance Criteria (Research-to-Execution Gate) | Dependencies |
|---|---|---|---|---|---|---|
| ACT-019 | ✅ COMPLETE (2026-04-22) | P1 | Add manifest canonicalization + freeze-hash standard for circuit/training runs | Enables deterministic reproducibility and auditable rollback | Spec + reference implementation define canonical JSON, freeze hash algorithm, and provenance fields; sample manifests pass deterministic hash tests | Week 1 complete |
| ACT-020 | Research Phase - Not Week 1 | P1 | Introduce descriptor-based plugin registry beyond SHA-256 verifier | Unlocks secure circuit optimizer/custom-gate plugin growth | Plugin descriptor schema includes id/version/contract/capabilities/schema hashes; at least one non-security plugin spec drafted | ACT-019 |
| ACT-021 | Research Phase - Not Week 1 | P1 | Add lightweight gateway policy layer for multi-region quantum job routing | Improves cost/perf routing without heavy infra lock-in | Policy doc defines routing signals (cost, region, queue depth, fallback) and includes falsifiable routing simulations | ACT-019 |
| ACT-022 | ❌ REJECTED (2026-04-22) | — | ~~Pilot ConnectRPC/gRPC as optional transport for orchestration flows~~ | Rejected: REST + OpenAPI 3.1 remains the sole transport. See `research/PROTO_ASSESSMENT.md` for rejection rationale and reconsideration gate. | n/a | n/a |
| ACT-023 | Research Phase - Not Week 1 | P2 | Prototype swarm proposal/outcome feedback loop for distributed AGI orchestration | Provides controlled distributed adaptation pattern | Design doc includes leader/quorum assumptions, proposal lifecycle, dry-run path, and rollback conditions | ACT-021 |
| ACT-024 | Research Phase - Not Week 1 | P3 | Evaluate evolutionary optimization loop for circuit/search policy tuning | May improve optimization efficiency if benchmarked properly | Experimental harness defines fitness function, budget cap, and stop/rollback triggers with reproducible benchmark report | ACT-019, ACT-023 |
| ACT-025 | Research Phase - Not Week 1 | P3 | Assess eBPF-assisted routing only after software policy router baseline | Avoids premature infra complexity | Decision record compares baseline software router vs eBPF-assisted prototype using production-like traffic traces | ACT-021 |



## ACT-019 — Completion Record (2026-04-22)

**Status:** ✅ COMPLETE
**OpenAPI version:** bumped `1.1.0` → `1.2.0`.

### Deliverables

- `plugins/freeze_snapshot/entrypoint.py` — canonical JSON + SHA-256 freeze
  utility (stdlib-only). Exposes `canonicalize`, `freeze_hash`,
  `verify_freeze`, plus a CLI (`hash` / `verify` / `canonicalize`).
- `plugins/freeze_snapshot/README.md` — algorithm, API, CLI, integration,
  non-goals.
- `plugins/freeze_snapshot/test_vectors.json` — 11 anchor vectors
  (primitives, numeric canonicalization, Bell-state circuit, training job
  config) with expected freeze hashes.
- `tests/plugins/run_freeze_tests.py` — deterministic test runner
  (TEST-FREEZE-001..007). Result: **39 passed, 0 failed.**
- `openapi/openapi.yaml` @ v1.2.0:
  - New `FreezeHash` schema (pattern `^freeze:[a-f0-9]{64}$`).
  - New `FreezeResponse` schema (resourceId, resourceKind, freezeHash,
    algorithm, frozenAt, canonicalBytes).
  - Optional read-only `freezeHash` field on `CircuitCreateResponse`,
    `CircuitResource`, `TrainingJobResponse`, `TrainingResultsResponse`.
  - Four new endpoints:
    - `POST /circuits/{circuitId}/freeze` (scope `circuits.freeze`)
    - `GET  /circuits/{circuitId}/freeze` (scope `circuits.read`)
    - `POST /training/jobs/{trainingId}/freeze` (scope `training.freeze`)
    - `GET  /training/jobs/{trainingId}/freeze` (scope `training.read`)
  - Two new OAuth scopes: `circuits.freeze`, `training.freeze`.
- `docs/freeze-snapshot.md` — why this exists, freeze-hash vs resource-ID
  contract, API surface, integration examples, non-goals.
- `FALSIFIABLE_TESTS.md` — TEST-FREEZE-001..007 added.
- `research/BLUEPRINT_V1.1_VERIFIED.md` — short confirmation of blueprint
  parity with repo (no image regeneration performed).
- `research/WINDOWS_UX_NOTES.md` — forward pointer for an interactive
  blueprint dashboard (placeholder **ACT-028**, not Week 2 scope).

### Validation

- `bash scripts/validate-openapi.sh` — passes (@redocly/cli lint + swagger-cli),
  only the two pre-existing `no-server-example.com` warnings from v1.1.0.
- `python3 tests/plugins/run_freeze_tests.py` — 39/39 tests pass.

### Next

**ACT-020 — descriptor-based plugin registry.** ACT-019 unlocks it: the
freeze hash primitive is the natural identity mechanism for plugin
artifacts (schemas, wasm modules, python entrypoints). With freeze hashes
available, a plugin descriptor can commit to a specific `schema_freeze`
and `entrypoint_freeze` and the registry loader can reject any plugin that
fails to match its declared hashes. See
`reference-implementations/plugin_descriptor_example.json` and
`reference-implementations/plugin_loading_mechanism.md` for the pattern
sketch that ACT-020 should execute against.
