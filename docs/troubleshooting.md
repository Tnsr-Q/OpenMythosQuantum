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
