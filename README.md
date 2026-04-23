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
- `runtime/server.py` — FastAPI reference runtime with middleware enforcement
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

## Testing

### Contract Tests

Automated validation of the OpenAPI specification:

```bash
# Run all contract tests
python3 tests/contract/run_all_contract_tests.py

# Or run individual test suites
python3 tests/contract/test_openapi_contract.py
python3 tests/contract/test_integration_examples.py
```

### Plugin Tests

```bash
python3 tests/plugins/run_freeze_tests.py
python3 tests/plugins/run_registry_tests.py
python3 tests/plugins/run_sha256_webhook_tests.py
```

See [Contract Testing Documentation](docs/contract-testing.md) for details.

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
| Contract testing suite | ✅ Completed | Automated OpenAPI validation + integration test examples |
| Runtime enforcement hardening | 🟡 In Progress | Reference FastAPI runtime now enforces idempotency, rate limits, webhook signatures, and OAuth scopes |


## Reference Runtime

Run a minimal executable bridge for the contract:

```bash
uvicorn runtime.server:app --host 0.0.0.0 --port 8080
```

The runtime includes:

- Redis-shaped idempotency middleware (in-memory fallback for local validation)
- Sliding-window rate limiting
- OAuth2 scope checks (header-based reference guard)
- Webhook signature verification via `plugins/sha256_verifier`

## Code Generation

Generate SDKs, server stubs, and docs from `openapi/openapi.yaml`:

```bash
bash scripts/generate-clients.sh
bash scripts/generate-server-stubs.sh
bash scripts/generate-api-docs.sh
```

Generated usage samples are in `examples/`.
