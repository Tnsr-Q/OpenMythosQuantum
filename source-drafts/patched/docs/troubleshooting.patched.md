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
- `simjob_...`
- `fbk_...`
- `rel_...`
- `ver_...`

### Optimization returned no result
Check `/verifications/{verificationId}`. Optimizations should not be returned as trusted output until verification passes.

### Live monitoring does not behave like a normal JSON endpoint
`/performance/live-monitor` is an SSE stream. Use an SSE client, not a one-shot REST parser.
