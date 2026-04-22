# Katopu Quantum AGI API

Production-ready unified API contract for:

- user and order management
- circuit creation, simulation, and optimization
- quantum compute jobs
- smart guidance
- encryption and decryption
- security and performance monitoring
- update orchestration
- AGI self-improvement runs
- training jobs, analytics, and notifications

## Structure

- `openapi/openapi.yaml` — source of truth API contract
- `config/.secrets.example` — safe placeholder secrets
- `scripts/validate-openapi.sh` — contract validation
- `plugins/sha256_verifier/` — webhook signature verifier plugin entrypoint
- `source-drafts/` — original normalized source drafts

## Authentication

Supported auth methods:

- `BearerAuth`
- `ApiKeyAuth`
- `OAuth2ClientCredentials`

Route-level requirements are defined in the OpenAPI spec.

## Validation

```bash
bash scripts/validate-openapi.sh
```

## Modernization Status

Tracked in [`ACTION_MANIFEST.md`](ACTION_MANIFEST.md).

| Area | Status | Notes |
|---|---|---|
| Contact info modernization | ✅ Completed | GitHub `Tnsr-Q` + ORCID `0009-0000-7999-7242` applied |
| Model name modernization | ✅ Completed | Production-grade model names introduced |
| JSON Schema/OpenAPI correctness | ✅ Completed (contract level) | Validation passes; only placeholder server-domain warnings remain |
| Idempotency-Key on POST | ✅ Completed | All POST operations include Idempotency-Key parameter |
| Cursor pagination | ✅ Completed | `GET /training/jobs` added with cursor/limit |
| Webhook SHA-256 signature standard | ✅ Completed | OpenAPI webhooks + verifier plugin entrypoint |
| Security baseline env flags | ✅ Completed | Rotation + TLS floor + webhook signature algorithm |
| Runtime enforcement hardening | ⏳ Pending | Requires gateway/service implementation |
