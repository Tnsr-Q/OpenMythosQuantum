# Proto / gRPC / ConnectRPC Assessment

> **Status: ❌ REJECTED (2026-04-22).**
>
> Katopu will **not** adopt gRPC or ConnectRPC at this time. The REST + OpenAPI 3.1 contract
> in `openapi/openapi.yaml` is the sole API transport. All recommendations below that
> previously suggested introducing gRPC/ConnectRPC are retained only as historical analysis.

## Rejection Rationale

1. **Single source of truth preserved.** Blueprint `openapi.yaml` is the canonical,
   human-reviewable contract. Introducing a parallel proto surface fractures governance.
2. **Cost / benefit does not clear the bar.** Current workloads (circuit submission,
   training jobs, webhooks) are well-served by REST + webhooks + cursor pagination.
   Streaming and low-latency control-plane needs can be met by Server-Sent Events /
   chunked HTTP / webhook callbacks without adopting a second RPC system.
3. **Avoid infrastructure lock-in.** `gatewayd` binary analysis shows ConnectRPC in a
   third-party component, not in Katopu. Observing a pattern is not justification to
   import it.
4. **Operational simplicity.** Runtime enforcement hardening (the one remaining
   modernization gap) is higher-value than a second transport.

## What This Means Concretely

- `ACT-022` (Pilot ConnectRPC/gRPC as optional transport) is **REJECTED**.
- No `.proto` files will be added to the repo.
- The `reference-implementations/go_gateway_pattern_notes.md` document is kept
  only as read-only reference material extracted from third-party binary analysis;
  its "ConnectRPC/gRPC capable gateway" shape is **not** a design target for Katopu.
- If streaming is ever required, the first option evaluated will be SSE or HTTP/2
  chunked responses layered on the existing REST contract — not a new RPC framework.

## Historical Discovery (kept for audit trail)

- No standalone `.proto` source files were found in `example yamls.zip`.
- Static analysis of `gatewayd` showed protobuf + ConnectRPC/gRPC symbols in that
  third-party binary only.
- Previous versions of this document recommended selective adoption. That
  recommendation is superseded by the rejection above.

## Reconsideration Gate

This decision may be revisited **only if all** of the following hold:

1. Runtime gateway is operational and REST p95 latency is measured as a bottleneck
   for a specific, named workload.
2. That workload's latency / streaming requirements cannot be met with SSE or
   HTTP/2 chunked responses.
3. A written cost accounting shows dual-contract governance overhead is acceptable.

Until then: **REST + OpenAPI 3.1 only.**
