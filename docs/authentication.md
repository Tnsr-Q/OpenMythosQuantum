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

## Webhook integrity

Incoming webhook events must include `X-Katopu-Signature` in format `sha256=<hex>`.
Verify using `HMAC-SHA256(secret=WEBHOOK_SIGNING_SECRET, payload=raw_body)`.
