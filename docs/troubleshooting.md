# Troubleshooting

## Common issues

### 401 Unauthorized
Check bearer token validity or `X-API-Key`.

### 403 Forbidden
Check OAuth2 scopes for the route.

### 400 Bad Request
Validate request body against `openapi/openapi.yaml`.

### 404 Not Found
Confirm resource identifier format:
- `usr_...`
- `ord_...`
- `cir_...`
- `trn_...`
- `qjob_...`

### 401 Webhook Signature Invalid
Verify `X-Katopu-Signature` format and HMAC SHA-256 digest against the raw request body.
