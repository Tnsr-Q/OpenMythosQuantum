# Deployment

## Minimum production requirements

- TLS termination
- JWT issuer and audience configured
- API key rotation policy
- database backups
- Redis persistence policy
- request tracing with `X-Request-Id`
- OpenAPI contract validation in CI

## Recommended CI checks

1. lint OpenAPI
2. validate OpenAPI
3. generate SDKs
4. run contract smoke tests

- webhook signature verification via HMAC SHA-256 (`X-Katopu-Signature`)
- secret rotation cadence (`SECRET_ROTATION_DAYS`)
- minimum TLS version enforcement (TLS 1.2+)
