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
