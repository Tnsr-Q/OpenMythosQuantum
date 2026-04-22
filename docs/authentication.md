# Authentication

## Supported schemes

### BearerAuth
JWT bearer token for user-facing clients.

### ApiKeyAuth
`X-API-Key` header for trusted service-to-service use.

### OAuth2 Client Credentials
Used for privileged automation and administrative flows.

## Scope examples

- `circuits.execute`
- `quantum.execute`
- `updates.write`
- `training.write`
- `agi.write`
