# Smart Integration Plan (Research Phase)

Goal: extract high-ROI patterns from provided infrastructure artifacts **without over-engineering** Katopu.

## Tier 1 (High-value, adopt next)

## 1) ~~Add optional gRPC/ConnectRPC transport for orchestration-heavy paths~~ ❌ REJECTED (2026-04-22)

> **This recommendation is rejected.** See `research/PROTO_ASSESSMENT.md` for the
> rejection rationale. REST + OpenAPI 3.1 remains the sole transport for Katopu.
> If streaming is required later, SSE / HTTP/2 chunked responses on the existing
> REST contract will be evaluated first.

**Decision**
- ❌ Do **not** introduce gRPC or ConnectRPC.
- ❌ Do not rewrite existing REST surface.
- ✅ Keep REST + OpenAPI as single transport.

## 2) Introduce plugin registry contract beyond SHA-256 verifier

**Why high ROI**
- Current plugin footprint is security verifier only.
- Research artifacts show mature plugin descriptors: version, capability flags, contract versions, schema hashes.

**Pragmatic scope**
- Define `plugin_descriptor` JSON schema for:
  - `id`, `version`, `contract_version`
  - `capabilities` (e.g., `supports_circuit_opt`, `supports_custom_gates`, `supports_cluster_compute`)
  - optional parameter schema + SHA-256 digest
- Candidate plugin classes:
  - circuit optimizer plugin
  - custom gate transformation plugin
  - training objective plugin

**Decision**
- ✅ Adopt descriptor-first plugin registration next iteration.

## 3) Implement snapshot/freeze manifest hashing for reproducibility

**Why high ROI**
- Directly improves experiment reproducibility, auditability, and rollback confidence.
- Maps perfectly to quantum circuit/model versioning.

**Pragmatic scope**
- Canonical JSON + SHA-256 freeze hash for run manifests.
- Capture provenance (`git_commit`, `build_id`, runtime env knobs).
- Optional strict input hash enforcement for critical runs.

**Decision**
- ✅ Adopt quickly for circuit/model manifests and AGI training runs.

## 4) Gateway/proxy policy layer for multi-region quantum job routing (lightweight first)

**Why high ROI**
- Multi-region routing is a natural fit for quantum job orchestration and budget constraints.
- Binary patterns show proposal/outcome feedback loop that can inspire policy routing.

**Pragmatic scope**
- Start with policy engine in API layer:
  - region affinity
  - cost ceiling checks
  - queue depth / fallback provider logic
- Keep infra simple at first (no eBPF dependency).

**Decision**
- ✅ Implement software policy router first, reserve deeper network tricks for later.

## Tier 2 (Medium-value, defer)

## 1) Swarm control pattern for distributed AGI runs

**Value**
- proposal/telemetry/outcome loops are useful for distributed optimizer agents.

**Why defer**
- introduces operational complexity (leader state, quorum, failure handling).
- should follow after baseline orchestrator reliability is proven.

**Deferred scope**
- leader epoch concept
- proposal queue with dry-run validation
- outcome feedback scoring for policy updates

## 2) Genetic/evolutionary optimization loop for circuit optimization

**Value**
- likely useful for automated hyperparameter and circuit topology search.

**Why defer**
- requires robust objective functions, evaluation harness, and compute budget control.
- premature before stronger baseline benchmarking.

**Deferred scope**
- mutation proposal model
- fitness summary scoring
- controlled mutation firewalls and rollback criteria

## 3) Proto-first internal contracts for orchestrator services

**Value**
- clearer typing and streaming semantics for internal high-throughput services.

**Why defer**
- no proto source files included in artifact drop; would require greenfield schema design and governance.

## Tier 3 (Low-value / skip for now)

## 1) eBPF-centric routing/data-plane mutation for early Katopu milestones

**Why low fit now**
- high kernel-level complexity and operational risk.
- weak direct impact on quantum model quality compared with algorithmic/plugin improvements.

**Decision**
- ❌ Skip for near-term roadmap; revisit only if network bottlenecks become proven blocker.

## 2) Full Darwinian control-plane replication

**Why low fit now**
- sophisticated, but broader than Katopu’s immediate product goals.
- risk of building orchestration machinery before measurable quantum/AGI gains.

**Decision**
- ❌ Avoid wholesale adoption; cherry-pick only measurable components.

## 3) Embedded-base64-everything registry format as default

**Why low fit now**
- portable but harder to review and diff in regular development flow.

**Decision**
- ❌ Prefer human-readable schema references in repo by default; use embedded snapshots only for signed release bundles.

## Recommended Implementation Sequence (Research-informed)

1. Add manifest canonicalization + freeze hash.
2. Add descriptor-based plugin contract for optimizer/custom-gate plugins.
3. Add lightweight routing policy layer for multi-region quantum jobs.
4. ~~Pilot one ConnectRPC/gRPC endpoint for streaming orchestration feedback.~~ **❌ REJECTED** — keep REST + OpenAPI; if streaming needed, use SSE / HTTP chunked over existing REST contract first.
5. Reassess swarm + genetic loops after baseline metrics show need.

## Success Criteria

- Quantum/circuit workflows become more reproducible (hash-anchored manifests).
- Plugin integration velocity improves without weakening security.
- Orchestration latency and routing reliability improve with minimal platform risk.
- Added complexity remains proportional to measurable ROI.
