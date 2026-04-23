# Infrastructure Analysis (Research Task)

> **Scope clarification:** This document describes patterns observed in a **third-party**
> binary (`gatewayd`). It does not prescribe Katopu's architecture. In particular, all
> references below to ConnectRPC, gRPC, protobuf transport, or eBPF routing describe
> what is present **in the third-party binary**, not what Katopu adopts.
> Katopu's API transport remains **REST + OpenAPI 3.1 only** (see
> `research/PROTO_ASSESSMENT.md` — gRPC/ConnectRPC adoption REJECTED 2026-04-22).

Date: 2026-04-22  
Scope analyzed:
- `/home/ubuntu/Uploads/gatewayd` (static analysis only; not executed)
- `/home/ubuntu/infrastructure-analysis` (extracted from `example yamls.zip`)

## 1) Extraction Status

- Extracted `example yamls.zip` into `/home/ubuntu/infrastructure-analysis/`.
- Archive contains two sets of files:
  - primary examples under `example yamls/`
  - macOS metadata under `__MACOSX/` (`._*` AppleDouble files; non-functional for runtime design)

## 2) Complete File Inventory

### 2.1 Binary Artifact

| Path | Type | Size | Apparent Purpose |
|---|---|---:|---|
| `/home/ubuntu/Uploads/gatewayd` | ELF 64-bit Go executable (not stripped, debug info present) | 13,835,138 bytes | Gateway daemon with ConnectRPC/gRPC, eBPF integration, swarm bridge control loops, telemetry/metrics, mutation lifecycle handling |

### 2.2 Infrastructure Example Files (Functional)

| Path | Type | Size | Apparent Purpose |
|---|---|---:|---|
| `example yamls/snap.boltz.json` | JSON | 12,197 | Snapshot container (`Boltz_snap`) with kernel descriptors + base64 schemas + SHA-256 integrity fields |
| `example yamls/ric.echo_search_sha256_hex.json` | JSON | 12,198 | Alternate/duplicate snapshot-style kernel registry payload with integrity-hashed schemas |
| `example yamls/experiment_workbench.v1.schema.json` | UTF-8 text (JSON schema content) | 4,858 | Envelope schema for `ric.experiment_manifest.v1` |
| `example yamls/ric.kernel_descriptor.b64.v1.json` | JSON | 2,765 | Kernel descriptor schema: capabilities + base64 schema payload model |
| `example yamls/registry_response.json` | Text JSON example | 1,823 | Registry list response using direct `$ref` schema pointers |
| `example yamls/ric_ui_hints.v1.json` | UTF-8 text (JSON schema content) | 3,445 | UI hints schema for dynamic UI form generation |
| `example yamls/workbench_Logic.v1.txt` | UTF-8 text | 1,529 | Canonicalization + freeze hash specification (deterministic reproducibility) |
| `example yamls/manifest_response.b64.v1.json` | Text JSON example | 2,209 | Registry response variant embedding base64 schemas + hash digests |
| `example yamls/kernal_descriptor.b64.v1.schema` | Text JSON schema content | 2,818 | Kernel descriptor schema (misspelled filename variant) |
| `example yamls/kernal_descriptor.b64.v1.json` | Text JSON schema content | 558 | Kernel registry list response schema referencing descriptor schema |
| `example yamls/ric.experiment_manifest.v1.json` | JSON | 2,403 | Concrete experiment manifest example (bindings, reproducibility, provenance, outputs) |
| `example yamls/perameters_manifest.json` | Text JSON schema content | 4,543 | Kernel parameter schema (echo search, validation/null tests/injection options) |

### 2.3 Non-Functional Metadata Files

`__MACOSX/example yamls/._*` files are all **AppleDouble metadata** (425 bytes each). These are packaging artifacts from macOS zip creation and can be ignored for architecture decisions.

## 3) gatewayd Binary Analysis (No Execution)

## 3.1 File Characteristics

- ELF x86-64 Linux executable
- Go build with debug symbols present (`not stripped`)
- Dynamically linked; interpreter `/lib64/ld-linux-x86-64.so.2`

## 3.2 Strong Signals from Strings

Observed string evidence indicates:

- **Transport/API stack**: ConnectRPC + gRPC/gRPC-Web + protobuf internals
  - `connectrpc.com/connect`
  - `application/grpc-web`, `Grpc-Status`, `ProtoMessage`
  - service-like paths: `tensorq.darwinian.v1.CortexGateway/UpdateAlphaRoute`, `.../StreamSimulation`

- **eBPF integration**:
  - `github.com/cilium/ebpf`, `github.com/cilium/ebpf/btf`
  - map/program symbols: `*ebpf.Map`, `*ebpf.Program`, `load BTF`, `routing_map`
  - metrics names: `tensorq_ebpf_map_entries`, `tensorq_ebpf_mutations_*`

- **Swarm bridge control plane**:
  - symbols under `internal/swarmbridge/client`
  - endpoints/ops inferred from strings: leader fetch, proposals fetch, telemetry post, freeze post, outcome post
  - health/quorum concepts: `Current swarm leader epoch`, quorum metrics

- **Mutation/evolution workflow signals**:
  - `darwinianv1.RouteMutation`
  - `Proposal`, `Outcome`, `FitnessSummary`, `UpdateAlphaRoute`
  - lifecycle metrics: mutations received/applied/rejected/failed

- **Security and networking controls**:
  - TLS/HTTP2 extensive usage (`tls.Config`, `ListenAndServeTLS`, ALPN/http2)
  - auth header handling (`Authorization`, `BasicAuth`)
  - strict transport hints (`strict-transport-security`)

## 4) Architecture Patterns Identified

## 4.1 Gateway Pattern

A **control gateway** appears to mediate between frontend traffic and swarm/eBPF mutation application:

- northbound: HTTP/2 + ConnectRPC/gRPC style API
- southbound: swarm bridge proposal/telemetry/freeze/outcome loops
- side-channel: Prometheus metrics and operational health endpoints

For Katopu, this maps well to a future **multi-region quantum job routing gateway** with policy + telemetry feedback loops.

## 4.2 Schema Pattern (Proto + JSON-Schema coexistence)

- Example bundle is strongly **JSON-schema-centric** for kernel/manifest/UI contracts.
- Binary indicates **protobuf/ConnectRPC transport** in control plane.

This suggests a split pattern:
- machine transport: protobuf/gRPC or ConnectRPC
- human-editable experiment contract: JSON schemas + JSON manifests

## 4.3 Config and Registry Pattern

- Registry payloads enumerate kernels/plugins with capabilities and contracts.
- Two distribution styles exist:
  1. `$ref` pointers to separate files
  2. base64-embedded schemas with SHA-256 digests

This is a robust pattern for offline portability + integrity verification.

## 5) Plugin Patterns (bolts.snap model)

`Boltz_snap` pattern in `snap.boltz.json` shows:

- snapshot envelope with `snapshot_name`, `snapshot_version`, `snapshot_sha256_hex`
- plugin/kernel descriptors include:
  - semantic ID (`name`, `version`, `contract_version`)
  - capability matrix (`supports_cluster_compute`, etc.)
  - embedded parameter/UI schemas (base64)
  - per-schema SHA-256 digests

**Interpretation:** plugin registry is treated as a signed/versioned artifact rather than ad-hoc config.

## 6) Snapshot / Freeze Mechanisms

From `workbench_Logic.v1.txt` and manifest schema:

- canonical JSON rules are specified (sorted keys, no whitespace, UTF-8, finite numbers, no NaN/Inf)
- `freeze_hash = sha256(canonical_json(manifest))`
- input hash checks can be enforced via `reproducibility.require_hash_check`
- manifests include provenance fields (`git_commit`, `build_id`, `orchestrator`)

This is directly reusable for deterministic circuit/model run versioning.

## 7) eBPF Patterns Detectable from Config/Binary

- Direct examples in zip are not eBPF programs, but binary strings clearly indicate eBPF map/program operations and BTF-aware loading.
- Mutation path appears to write routing decisions into pinned eBPF maps (`routing_map` references).
- Observability is first-class via eBPF mutation counters and map entry gauges.

For Katopu: eBPF is likely only useful in network/control-plane optimization, not core quantum simulation logic.

## 8) Swarm Control Patterns

Detected swarm control traits:

- leader election/epoch and quorum-health checks
- proposal retrieval + forwarding
- outcome reporting and telemetry batches
- freeze proposal/ack flows for coordinated state control

This supports a **feedback-driven distributed orchestrator** model for AGI runs.

## 9) Genetic / Evolutionary References

Evidence is inferential but strong:

- namespace and symbols: `darwinianv1`, `FitnessSummary`, `UpdateAlphaRoute`, proposal/outcome cycles
- mutation-centric data model with acceptance/rejection checks and rollback semantics

No explicit GA equations/operators (selection/crossover/mutation rates) were present in the extracted config files, but control-plane naming indicates evolutionary optimization concepts in routing policy.

## 10) Security Patterns

Strong patterns found:

- pervasive TLS and HTTP/2 support
- auth/header handling (authorization pathways)
- integrity checks via SHA-256 digests for schemas and input assets
- deterministic canonicalization to prevent ambiguity attacks in hashing
- explicit freeze + outcome reporting supports auditability and rollback trails

## 11) Gaps / Cautions

- No raw `.proto` files were present in `example yamls.zip`; proto usage is inferred from binary symbols.
- Several filenames have typos (`kernal`, `perameters`) and mixed documentation prefixes; treat examples as concept references, not drop-in production assets.
- Some files are narrative/spec text with JSON embedded, not pure machine-ready JSON documents.

## 12) Pragmatic Relevance to Katopu

High-confidence reusable ideas:

1. Versioned plugin registry with capability flags + schema hashes.
2. Canonical manifest freeze hash for deterministic experiment/circuit reproducibility.
3. Swarm-style telemetry+proposal loop for distributed AGI orchestration.

Lower-confidence / defer:

- adopting eBPF-heavy routing internals early (high ops burden vs Week 1/2 priorities).
