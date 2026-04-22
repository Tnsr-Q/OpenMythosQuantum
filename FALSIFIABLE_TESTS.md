# Falsifiable Tests Checklist

## Contact + Identity Modernization

- [ ] `grep -R -n "<legacy_contact_markers>|<legacy_contact_email_prefix>|<legacy_contact_username>" /home/ubuntu/katopu-api` returns no matches.
- [ ] `grep -R -n "github.com/Tnsr-Q" /home/ubuntu/katopu-api/openapi /home/ubuntu/katopu-api/README.md` returns matches.
- [ ] `grep -R -n "0009-0000-7999-7242" /home/ubuntu/katopu-api/openapi /home/ubuntu/katopu-api/README.md` returns matches.

## Model Name Modernization

- [ ] `grep -R -n "<legacy_model_a>\|<legacy_model_b>\|<legacy_model_c>" /home/ubuntu/katopu-api` returns no matches.
- [ ] `grep -R -n "gpt-4-turbo\|claude-3-opus\|gemini-1.5-pro" /home/ubuntu/katopu-api/config /home/ubuntu/katopu-api/openapi` returns matches.

## OpenAPI Contract Correctness

- [ ] `bash scripts/validate-openapi.sh` exits with status code 0.
- [ ] `openapi/openapi.yaml` contains `openapi: 3.1.0` and `jsonSchemaDialect: https://json-schema.org/draft/2020-12/schema`.

## Idempotency-Key Coverage

- [ ] Python assertion: every POST operation includes `#/components/parameters/IdempotencyKey`.

Suggested command:
```bash
python3 - <<'PY'
import yaml
s=yaml.safe_load(open('openapi/openapi.yaml'))
missing=[]
for p,item in s['paths'].items():
    if 'post' in item:
        refs=[x.get('$ref') for x in item['post'].get('parameters',[]) if isinstance(x,dict)]
        if '#/components/parameters/IdempotencyKey' not in refs:
            missing.append(p)
print('missing_post_idempotency=',missing)
assert not missing
PY
```

## Pagination Contract

- [ ] `GET /training/jobs` exists in OpenAPI.
- [ ] `GET /training/jobs` defines `cursor` and `limit` query parameters.
- [ ] Response schema references `PaginatedTrainingJobsResponse`.

## Webhook Signature Integrity (SHA-256)

- [ ] OpenAPI includes top-level `webhooks` with required `X-Katopu-Signature` header pattern `^sha256=[A-Fa-f0-9]{64}$`.
- [ ] Plugin verifier returns VERIFIED for known-good payload/signature.

Example deterministic check (realistic webhook payload fixtures):
```bash
python3 tests/plugins/run_sha256_webhook_tests.py
```
Expected output includes:
- `PASS: training.completed valid signature`
- `PASS: notification.delivered valid signature`
- `PASS: training.completed tampered payload`
- `PASS: notification.delivered wrong secret`
- `All SHA-256 webhook verifier checks passed.`

## Security Baseline Flags

- [ ] `config/.secrets.example` includes `SECRET_ROTATION_DAYS`.
- [ ] `config/.secrets.example` includes `TLS_MIN_VERSION=1.2`.
- [ ] `config/.secrets.example` includes `WEBHOOK_SIGNATURE_ALGORITHM=hmac-sha256`.
