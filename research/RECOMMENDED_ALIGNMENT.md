# Recommended Alignment: Blueprint ↔ Repo

**Companion to:** `research/BLUEPRINT_VERIFICATION.md`
**Date:** 2026-04-22

This document proposes how to resolve the discrepancies between
`visualization prototype.png` (the blueprint) and `openapi/openapi.yaml`
(the actual contract at version **1.1.0**).

---

## 1. Options

### Path A — Align repo to blueprint

Rename paths and add the missing endpoints so the contract matches the picture.

**Changes required in `openapi/openapi.yaml`:**

- Rename path prefixes: `/quantum/jobs` → `/qc/jobs`, `/security/*` → `/crypto/*`, `/agi/self-improvement/runs` → `/agi/runs`.
- Rename operations: `POST /guidance/assist` → `POST /guidance/query`, `POST /notifications` → `POST /notifications/send`.
- Change verb: `GET /updates/check` → `POST /updates/check`.
- Add endpoints: `GET /users`, `GET /orders`, `POST /qc/jobs/{id}/cancel`, `GET /qc/backends`, `GET /guidance/sessions`, `GET /guidance/sessions/{id}`, `POST /crypto/keys`, `GET /monitoring/metrics`, `GET /monitoring/logs`, `GET /monitoring/traces`, `GET /security/events`, `GET /updates/history`, `GET /updates/status`, `GET /agi/runs`, `GET /agi/runs/{id}`, `POST /agi/runs/{id}/stop`, `GET /analytics/metrics`.
- Decide whether to keep repo-only endpoints (`/healthz`, `/dashboard/metrics`, `/monitoring/security`, `/monitoring/performance`, `/training/jobs/{id}/{stop,results,recommendations,analytics}`) or delete them.

| Pros | Cons |
|---|---|
| Blueprint becomes exact contract reference | Breaking change for any consumer using 1.1.0 |
| Consistent namespace with blueprint visuals | `/qc` is an ambiguous abbreviation (quality control? quantum compute?); `/quantum` is clearer |
| Fewer orphan endpoints in docs | Adds 17 new path stubs that need schemas, handlers, tests |
| | Adds more surface than current workloads need |
| | Effort: **~1.5–2 weeks** for spec rewrite + fixtures + CI updates |

### Path B — Align blueprint to repo

Redraw the blueprint to reflect the repo as it actually exists at 1.1.0.

**Changes required in `visualization prototype.png` (regenerate):**

- Update version badge: 1.0.0 → **1.1.0**.
- Area 3: rename tile to `/quantum/jobs` (drop `/cancel`, `/backends`).
- Area 4: show single `POST /guidance/assist` (drop `/sessions*`).
- Area 5: rename to "Security: encrypt/decrypt" at `/security/*` (drop `/crypto/keys`).
- Area 6: replace with repo reality (`POST /monitoring/security`, `POST /monitoring/performance`, `GET /dashboard/metrics`); remove logs/traces/events tiles.
- Area 7: `GET /updates/check`, `POST /updates/apply` (drop `/history`, `/status`).
- Area 8: `POST /agi/self-improvement/runs` (drop GET list / stop).
- Area 9: show `POST /training/jobs`, `GET /training/jobs` (cursor), `GET /training/jobs/{id}/{stop,results,recommendations,analytics}`, `POST /notifications`; drop `/analytics/metrics` and `/notifications/send`.
- Add `/healthz` to an "Operations" strip.

| Pros | Cons |
|---|---|
| Zero code/contract change | Loses blueprint's clean 9-quadrant symmetry |
| No breaking change for API consumers | Visual rendering cost (re-export PNG) |
| Keeps the richer repo semantics (per-job analytics, stop/results/recommendations) | Some blueprint ideas lost (queue management, cancel, audit log) |
| Effort: **1–2 days** (regenerate visual + update `README.md` reference) | |

### Path C — Hybrid (**RECOMMENDED**)

Keep the repo as the source of truth, but selectively add blueprint endpoints that
provide real operational value. Update the blueprint to reflect the hybrid state.

**Repo changes (additive, non-breaking):**

1. **Keep existing paths.** No renames (`/quantum`, `/security`, `/agi/self-improvement` stay).
2. **Add high-value GET list endpoints** (idempotent, non-breaking):
   - `GET /users` — list (cursor + limit).
   - `GET /orders` — list (cursor + limit).
   - `GET /quantum/jobs` — list (cursor + limit).
   - `GET /agi/self-improvement/runs` — list (cursor + limit).
3. **Add cancel/stop endpoints** (operationally important):
   - `POST /quantum/jobs/{jobId}/cancel`.
   - `POST /agi/self-improvement/runs/{runId}/stop`.
4. **Add status / history observability:**
   - `GET /updates/status` (already semantically covered by `GET /updates/check` — evaluate before duplicating).
   - `GET /updates/history` — audit log of applied updates.
5. **Do NOT add** `/crypto/keys`, `/monitoring/logs`, `/monitoring/traces`, `/security/events`,
   `/analytics/metrics`, `/qc/backends`, `/guidance/sessions*`, `/notifications/send`.
   These are out of scope for the current contract — revisit only if a concrete consumer
   needs them.

**Blueprint changes (regenerate):**

- Bump version to **1.1.0** (or **1.2.0** once the hybrid additions ship).
- Correct path labels to real repo paths (`/quantum/jobs`, `/security/encrypt`,
  `/agi/self-improvement/runs`, `/guidance/assist`, `POST /notifications`).
- Add new tiles for the hybrid additions (list + cancel + stop).
- Remove tiles that don't reach the recommendation (logs/traces/events/keys/backends/sessions).
- Show `/healthz` as an ops strip.

| Pros | Cons |
|---|---|
| No breaking change; existing clients unaffected | Blueprint needs re-rendering anyway |
| Adds real operational value (list, cancel, stop, update history) | Two edits (repo + blueprint) instead of one |
| Keeps blueprint's 9-area taxonomy as the UX model | Contract review + tests for new endpoints |
| Effort: **~3–5 days** for repo additions, **1 day** for blueprint re-render | |

---

## 2. Decision Matrix

Rows are weighted criteria; columns are the three paths.

| Criterion | Weight | Path A (repo→blueprint) | Path B (blueprint→repo) | Path C (hybrid) |
|---|---:|---:|---:|---:|
| Contract stability (no break) | 30% | 1 (breaks 1.1.0 clients) | 5 | 5 |
| Operational completeness | 25% | 5 | 2 (loses cancel/list/stop) | 4 (adds the useful ones) |
| Implementation effort | 20% | 1 (~2 weeks) | 5 (<2 days) | 3 (~1 week total) |
| Naming clarity | 10% | 2 (`/qc` ambiguous) | 4 | 4 |
| Documentation / UX value | 10% | 4 | 3 | 5 (blueprint + reality aligned) |
| Future-proofing | 5% | 3 | 3 | 4 |
| **Weighted score** | | **2.45** | **3.85** | **4.25** |

**Winner: Path C (Hybrid).**

---

## 3. Recommendation

**Adopt Path C.** Concretely:

1. **Do not rename any existing path.** `info.version` stays **1.1.0** for non-breaking release; bump to **1.2.0** when the additions below land.
2. **Week-2 additive OpenAPI work** (ordered by value):
   1. `GET /quantum/jobs` (cursor/limit) — parity with `GET /training/jobs`.
   2. `POST /quantum/jobs/{jobId}/cancel`.
   3. `GET /agi/self-improvement/runs` (cursor/limit) + `POST /agi/self-improvement/runs/{runId}/stop`.
   4. `GET /users` (cursor/limit), `GET /orders` (cursor/limit).
   5. `GET /updates/history` (cursor/limit).
3. **Regenerate the blueprint PNG** after (1)–(5) ship, with:
   - `info.version = 1.2.0`
   - repo-correct path labels
   - remove endpoints that were not adopted (crypto keys, monitoring logs/traces, security events, analytics metrics, qc backends, guidance sessions, notifications/send)
4. **gRPC/ConnectRPC remains REJECTED** (see `research/PROTO_ASSESSMENT.md`).
5. **Runtime enforcement hardening** is the next modernization gap to close — unrelated to this alignment work but must ship before the blueprint can advertise "8 Passed, 0 Pending".

---

## 4. Non-Goals

- Renaming stable 1.1.0 paths.
- Introducing a second transport (gRPC / ConnectRPC).
- Implementing `/monitoring/logs|traces|events`, `/analytics/metrics`, `/crypto/keys`, `/qc/backends`, `/guidance/sessions*`, or `/notifications/send` unless a concrete consumer use case is presented.
