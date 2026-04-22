# Falsifiable Tests Checklist

## Contact + Identity Modernization

- [ ] `grep -R -n "<legacy_contact_markers>|<legacy_contact_email_prefix>|<legacy_contact_username>" /home/ubuntu/katopu-api` returns no matches.
- [ ] `grep -R -n "tnsr_q@icloud.com" /home/ubuntu/katopu-api` returns at least one match.

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

Example deterministic check:
```bash
cat > /tmp/payload.json <<'JSON'
{"ok":true}
JSON
SIG=$(python3 - <<'PY'
import hmac, hashlib
secret='test-secret'
payload=open('/tmp/payload.json','rb').read()
print('sha256='+hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest())
PY
)
python3 plugins/sha256_verifier/entrypoint.py --secret test-secret --signature "$SIG" --payload-file /tmp/payload.json
```
Expected output: `VERIFIED`

## Security Baseline Flags

- [ ] `config/.secrets.example` includes `SECRET_ROTATION_DAYS`.
- [ ] `config/.secrets.example` includes `TLS_MIN_VERSION=1.2`.
- [ ] `config/.secrets.example` includes `WEBHOOK_SIGNATURE_ALGORITHM=hmac-sha256`.
