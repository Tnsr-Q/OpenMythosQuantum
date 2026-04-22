# Action Manifest — Katopu API Modernization

## Executive Summary

The repository has been upgraded for high-confidence contract modernization:
- outdated ownership/contact references removed,
- legacy model names replaced with production-grade alternatives,
- OpenAPI modern patterns added (idempotency, pagination, webhook signature integrity),
- SHA-256 verifier plugin introduced for end-to-end webhook authenticity checks.

OpenAPI validation now passes with only non-blocking placeholder-domain warnings.

## Prioritized Actions

| Priority | Action | Acceptance Criteria (Falsifiable) | Risk | Complexity | Dependencies | Rollback Strategy |
|---|---|---|---|---|---|---|
| P0 | Contact info modernization | `grep -R "<legacy_contact_markers>|<legacy_contact_email_prefix>|<legacy_contact_username>" /home/ubuntu/katopu-api` returns zero matches | Low | Low | None | Revert commit touching contact replacements |
| P0 | Model name modernization | `grep -R "<legacy_model_a>\|<legacy_model_b>\|<legacy_model_c>" /home/ubuntu/katopu-api` returns zero matches | Low | Low | None | Revert config/spec model-name changes |
| P0 | POST idempotency contract | Every POST operation in OpenAPI references `#/components/parameters/IdempotencyKey` | Low | Medium | OpenAPI schema edit | Revert OpenAPI operation parameter additions |
| P0 | Cursor pagination for list APIs | `GET /training/jobs` exists with `cursor` + `limit` params and paginated response schema | Low | Medium | New schema + endpoint | Remove endpoint and pagination schemas |
| P0 | Webhook signature integrity (SHA-256) | OpenAPI has `webhooks` with required `X-Katopu-Signature` header pattern `^sha256=` and verifier plugin returns VERIFIED on known-good input | Low | Medium | Shared secret in config | Revert webhooks + plugin directory |
| P1 | Security operations defaults | `.secrets.example` includes `SECRET_ROTATION_DAYS`, `TLS_MIN_VERSION`, `ENFORCE_HSTS` | Low | Low | None | Revert env-example edits |
| P1 | README modernization tracking | README contains `Modernization Status` section with explicit status table | Low | Low | Action manifest finalized | Revert README section |
| P2 | Runtime enforcement implementation | Gateway/service actually enforces webhook signature, idempotency persistence, and scope claims | Medium | High | Engineering implementation | Feature flags + staged rollout |

## Dependency Graph (Simplified)

1. OpenAPI components (`IdempotencyKey`, pagination schemas, webhook schemas)
2. Path operation adoption (POST header references, list endpoint)
3. Documentation alignment (`README`, auth/deployment/troubleshooting docs)
4. Runtime plugin/tooling (SHA-256 verifier entrypoint)
5. Falsifiable test checklist finalization

## Risk Assessment Notes

- **Schema-level changes** are low operational risk because they are additive and contract-forward.
- **List endpoint introduction** may require backend implementation if deployed beyond mock/stub mode.
- **Webhook signing** can fail if consumers hash transformed JSON instead of raw body bytes.

## Estimated Effort

- Completed P0/P1 contract modernization: ~1 engineer-day equivalent.
- Remaining P2 runtime hardening: ~3–7 engineer-days depending on gateway/service stack.

## Rollback Strategy (Global)

- Use git commit boundaries per modernization wave.
- If regressions occur:
  1. revert webhook/idempotency/pagination commit,
  2. keep contact/model text upgrades intact,
  3. reintroduce changes behind feature flags after backend readiness.
