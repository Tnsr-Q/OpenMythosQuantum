# Go Gateway Pattern Notes (Extracted from `gatewayd` static strings)

> **⚠️ Reference material only. NOT a Katopu design target.**
>
> This file preserves static-analysis notes taken from a third-party `gatewayd`
> binary. The ConnectRPC / gRPC transport pattern below is **explicitly rejected**
> for Katopu (see `research/PROTO_ASSESSMENT.md`). Katopu will continue to use
> **REST + OpenAPI 3.1** as its sole transport. If streaming is ever required,
> SSE or HTTP/2 chunked responses over the existing REST contract are the first
> option to evaluate.
>
> The notes are kept for historical auditability only.

## Observed Architectural Shape (in the third-party binary)

- ConnectRPC/gRPC capable gateway  ← **not adopted by Katopu**
- HTTP/2 + TLS transport stack
- Prometheus metrics exposure
- Separate swarm bridge client loops for:
  - leader state fetch
  - alpha proposal fetch
  - telemetry posting
  - freeze proposal posting
  - outcome posting

## Observed Endpoint/Procedure Signals (third-party, for reference only)

- `tensorq.darwinian.v1.CortexGateway/UpdateAlphaRoute`  (ConnectRPC procedure — not used)
- `tensorq.darwinian.v1.CortexGateway/StreamSimulation`  (ConnectRPC procedure — not used)
- `/v1/leader`
- `/v1/proposals/alpha`
- `/v1/proposals/freeze`
- `/v1/telemetry`
- `/v1/outcomes`
- `/metrics`

## What Katopu Actually Takes from This

**Adopted (transport-agnostic patterns):**

- Separation of background control loops from request-serving handlers.
- Prometheus-style metrics endpoint for observability.
- TLS 1.2+ baseline (already in `.secrets.example`).

**Rejected:**

- ConnectRPC / gRPC transport.
- Parallel proto-defined contract alongside OpenAPI.
- Any "dual-transport" architecture.

## Pseudo-Go Pattern (transport-neutral, REST-only)

```go
// Pattern only — transport is plain HTTP/REST for Katopu.
type ControlGateway struct {
    router        http.Handler // serves REST endpoints from openapi.yaml
    policyEngine  PolicyEngine
    backgroundJobs BackgroundJobs // telemetry/routing/health loops
    metrics       Metrics
}

func (g *ControlGateway) Start(ctx context.Context, addr string, tlsCfg *tls.Config) error {
    // 1) Start background control loops (telemetry, routing, health).
    //    These are internal goroutines, NOT gRPC streams.
    cancelLoops, errCh := g.backgroundJobs.StartLoops(ctx)
    defer cancelLoops()

    go func() {
        for err := range errCh {
            g.metrics.Inc("control_loop_errors_total")
            log.Printf("control loop error: %v", err)
        }
    }()

    // 2) Serve REST (OpenAPI-contract) APIs + Prometheus /metrics over HTTPS.
    srv := &http.Server{
        Addr:      addr,
        Handler:   g.router,
        TLSConfig: tlsCfg,
    }
    return srv.ListenAndServeTLS("", "")
}
```

## Why Still Useful (despite the rejection)

- Separates control loops from request serving — applies equally to a REST-only service.
- Supports multi-region job routing decisions without any RPC framework.
- Telemetry-driven policy updates can be fed via REST callbacks + webhooks.
