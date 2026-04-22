# Deployment

## Minimum production requirements

- TLS termination
- JWT issuer and audience configured
- API key rotation policy
- database backups
- Redis persistence policy
- request tracing with `X-Request-Id`
- OpenAPI contract validation in CI
- outbound webhook signing and retry policy
- deterministic verification workers for optimization output
- async job workers for heavy simulation requests

## Recommended CI checks

1. lint OpenAPI
2. validate OpenAPI
3. generate SDKs
4. run contract smoke tests
5. run example payload conformance tests
6. verify release and rollback playbooks
