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
