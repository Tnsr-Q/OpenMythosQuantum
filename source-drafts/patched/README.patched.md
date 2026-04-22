# Katopu Quantum AGI API

Patched production-ready unified API contract for:

- user and order management
- circuit creation, analysis, simulation, parallel simulation, and optimization
- deterministic verification of LLM-assisted circuit optimization
- quantum compute jobs
- smart guidance
- encryption and decryption
- security and performance monitoring
- feedback collection and curated model updates
- release and rollback controls
- AGI self-improvement runs
- training jobs, analytics, notifications, SSE, and webhooks

## Structure

- `openapi/openapi.yaml` — source of truth API contract
- `config/.secrets.example` — safe placeholder secrets
- `scripts/validate-openapi.sh` — contract validation
- `source-drafts/` — original normalized source drafts
- `docs/quantum-validity.md` — mathematical and architectural validity notes
- `docs/webhooks.md` — webhook and SSE integration guide

## Key patches in v1.1.0

- adds `/circuits/{circuitId}/analyze`
- adds async `/circuits/{circuitId}/parallel-simulate`
- adds `/simulation-jobs/{jobId}`
- adds `/feedback`, `/feedback/{feedbackId}`
- adds `/analyze/performance`, `/models/update`
- adds `/versions/release`, `/versions/rollback`
- adds `/verifications/{verificationId}`
- adds top-level OpenAPI `webhooks`
- documents deterministic verification as mandatory for optimization results
- documents Hadamard normalization correction required in scientific background material

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
