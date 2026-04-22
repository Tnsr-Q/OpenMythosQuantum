# Webhooks and live monitoring

## Top-level webhooks

The OpenAPI contract defines these webhook payloads:

- `simulationCompleted`
- `trainingCompleted`
- `optimizationVerified`
- `monitoringAlert`

## Live monitoring

Use `GET /performance/live-monitor` for Server-Sent Events (SSE) when continuous telemetry is needed.

## Why both exist

- SSE is useful for interactive dashboards and operator consoles.
- Webhooks are better for automation and back-end integrations.

## Retry and signing

In production:
- sign webhook payloads
- store delivery attempts
- use retry with backoff
- ensure idempotent webhook consumers
