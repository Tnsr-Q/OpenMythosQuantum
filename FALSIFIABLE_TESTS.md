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



## Freeze / Snapshot Hashing (ACT-019)

Exercised by `python3 tests/plugins/run_freeze_tests.py`. Expected tail:
`ALL FREEZE TESTS PASSED`.

### TEST-FREEZE-001: Canonical serializer produces stable output across key reorderings

- [ ] Two Python dicts with identical keys/values but different insertion
      order produce byte-identical canonical JSON.
- [ ] Nested objects reordered at any depth produce the same freeze hash.
- [ ] Array element order IS significant (`[1,2,3]` and `[3,2,1]` hash
      differently — explicit contract).

### TEST-FREEZE-002: Whitespace in input does not change hash

- [ ] `json.loads` of a compact JSON string and a pretty-printed JSON
      string produce objects that canonicalize to identical bytes.
- [ ] Freeze hashes of the two parsed objects match.

### TEST-FREEZE-003: Numeric canonicalization

- [ ] `freeze_hash(1) == freeze_hash(1.0)`
- [ ] `freeze_hash(0) == freeze_hash(-0) == freeze_hash(-0.0) == freeze_hash(0.0)`
- [ ] Integer-valued floats nested in a manifest hash identically to the
      integer form.
- [ ] `NaN` and `Infinity` raise `ValueError` during canonicalization.
- [ ] Booleans are NOT coerced to `0`/`1` (`freeze_hash(True) != freeze_hash(1)`).

### TEST-FREEZE-004: Known Bell-state circuit produces expected freeze hash

- [ ] The 2-qubit Bell-state circuit vector in
      `plugins/freeze_snapshot/test_vectors.json` hashes to
      `freeze:95fcc2bdfb71b80a59ed5628871dce2fc9e9f0b857d7f6b90dfc5338c17e2f68`.
- [ ] `verify_freeze(bell, expected)` returns `True`.

### TEST-FREEZE-005: Single-field change produces different hash (tamper detection)

- [ ] Changing a single gate target in the Bell-state circuit → different
      freeze hash; `verify_freeze` against the original anchor returns
      `False`.
- [ ] Changing `learningRate` in the anchor training job config → different
      freeze hash; `verify_freeze` returns `False`.
- [ ] Adding an extra field (e.g. a comment) → different hash (no silent
      ignore).
- [ ] Malformed expected hashes (wrong prefix, wrong length, non-hex) →
      `verify_freeze` returns `False` (no exception).

### TEST-FREEZE-006: All 4 new endpoints present in OpenAPI spec

```bash
grep -c '/circuits/{circuitId}/freeze:'         openapi/openapi.yaml   # == 1
grep -c '/training/jobs/{trainingId}/freeze:'   openapi/openapi.yaml   # == 1
grep -c 'operationId: freezeCircuit'            openapi/openapi.yaml   # == 1
grep -c 'operationId: getCircuitFreeze'         openapi/openapi.yaml   # == 1
grep -c 'operationId: freezeTrainingJob'        openapi/openapi.yaml   # == 1
grep -c 'operationId: getTrainingJobFreeze'     openapi/openapi.yaml   # == 1
```

- [ ] `FreezeHash` schema present with pattern `^freeze:[a-f0-9]{64}$`.
- [ ] `FreezeResponse` schema present with required fields `resourceId`,
      `resourceKind`, `freezeHash`, `algorithm`, `frozenAt`.
- [ ] OAuth scopes `circuits.freeze` and `training.freeze` declared.

### TEST-FREEZE-007: OpenAPI validates cleanly at v1.2.0

```bash
grep -n 'version: 1.2.0' openapi/openapi.yaml | head -1   # line 6
bash scripts/validate-openapi.sh
```

- [ ] `info.version == 1.2.0`.
- [ ] `@redocly/cli lint` reports only the two pre-existing
      `no-server-example.com` warnings (no new warnings, no errors).
- [ ] `swagger-cli validate` reports the spec as valid.



## Plugin Registry (ACT-020)

Exercised by `python3 tests/plugins/run_registry_tests.py`. Expected tail:
`ALL REGISTRY TESTS PASSED`.

### TEST-REG-001: descriptor.schema.json validates both existing plugin descriptors

- [ ] `plugins/sha256_verifier/plugin.json` passes `descriptor.schema.json`.
- [ ] `plugins/freeze_snapshot/plugin.json` passes `descriptor.schema.json`.
- [ ] Removing a required field (`author`) → schema rejects.
- [ ] Adding an unknown field → `additionalProperties: false` rejects.
- [ ] Malformed capability (single segment) → schema rejects.
- [ ] Bad integrity prefix (e.g. `md5:...`) → schema rejects.
- [ ] Invalid `lifecycle` value → schema rejects.

### TEST-REG-002: registry.py lists 2 plugins

```bash
python3 plugins/registry.py list
```

- [ ] Output lists exactly 2 plugins.
- [ ] `sha256_verifier` present with version `1.0.0`, lifecycle `active`.
- [ ] `freeze_snapshot` present with version `1.0.0`, lifecycle `active`.

### TEST-REG-003: registry verifies integrity of both plugins

```bash
python3 plugins/registry.py verify
```

- [ ] Exit code 0.
- [ ] `OK    sha256_verifier`
- [ ] `OK    freeze_snapshot`
- [ ] Recomputed SHA-256 matches the hash recorded in each `plugin.json`.

### TEST-REG-004: registry rejects tampered descriptor / entrypoint

- [ ] Appending bytes to `entrypoint.py` → `verify_integrity()` returns
      `False` for that plugin.
- [ ] Forging the recorded hash in `plugin.json` (schema-valid but wrong)
      → `verify_integrity()` still returns `False` because the forged
      hash ≠ actual on-disk SHA-256.
- [ ] Unchanged plugins continue to verify `True` in the same run.

### TEST-REG-005: capability lookup finds sha256_verifier by "webhook.verify.sha256"

```bash
python3 plugins/registry.py find --capability=webhook.verify.sha256
```

- [ ] Returns exactly 1 plugin: `sha256_verifier`.
- [ ] `find --capability=nonexistent.capability` returns exit code 1.
- [ ] Revoked plugins are excluded from capability results.

### TEST-REG-006: capability lookup finds freeze_snapshot by "hash.freeze.sha256"

```bash
python3 plugins/registry.py find --capability=hash.freeze.sha256
python3 plugins/registry.py find --capability=hash.canonicalize
```

- [ ] Both capabilities return exactly 1 plugin: `freeze_snapshot`.
- [ ] `freeze_snapshot` declares both capabilities in its descriptor.

### TEST-REG-007: OpenAPI v1.3.0 validates cleanly

```bash
grep -n 'version: 1.3.0' openapi/openapi.yaml | head -1
bash scripts/validate-openapi.sh
```

- [ ] `info.version == 1.3.0`.
- [ ] `@redocly/cli lint` reports no errors. Pre-existing warnings
      (`no-server-example.com` ×2, and the `no-ambiguous-paths` warning
      for `/plugins/capabilities/{capability}` vs `/plugins/{pluginId}/verify`
      — intentional path shape) remain as warnings.
- [ ] `swagger-cli validate` reports the spec as valid.

### TEST-REG-008: All 4 /plugins endpoints present in spec

```bash
grep -c '^  /plugins:'                              openapi/openapi.yaml   # == 1
grep -c '^  /plugins/{pluginId}:'                   openapi/openapi.yaml   # == 1
grep -c '^  /plugins/capabilities/{capability}:'    openapi/openapi.yaml   # == 1
grep -c '^  /plugins/{pluginId}/verify:'            openapi/openapi.yaml   # == 1
grep -c 'operationId: listPlugins'                  openapi/openapi.yaml   # == 1
grep -c 'operationId: getPlugin'                    openapi/openapi.yaml   # == 1
grep -c 'operationId: findPluginsByCapability'      openapi/openapi.yaml   # == 1
grep -c 'operationId: verifyPluginIntegrity'        openapi/openapi.yaml   # == 1
```

- [ ] `Plugin`, `PluginCapability`, `PluginLifecycle`, `PluginIntegrity`,
      `PluginEntrypoint`, `PaginatedPluginsResponse`, and
      `PluginIntegrityVerification` schemas are all defined.
- [ ] OAuth scopes `plugins.read` and `plugins.verify` declared under
      `OAuth2ClientCredentials`.
