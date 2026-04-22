# Authentication

## Supported schemes

### BearerAuth
JWT bearer token for user-facing clients.

### ApiKeyAuth
`X-API-Key` header for trusted service-to-service use.

### OAuth2 Client Credentials
Used for privileged automation and administrative flows.

## Scope examples

- `circuits.read`
- `circuits.write`
- `circuits.execute`
- `quantum.execute`
- `monitoring.write`
- `updates.write`
- `training.write`
- `agi.write`

## Operational guidance

- User-facing applications should prefer `BearerAuth`.
- Service-to-service workloads may use `ApiKeyAuth` where allowed.
- High-risk automation routes such as model updates, release, rollback, and monitoring should require OAuth2 scopes.
