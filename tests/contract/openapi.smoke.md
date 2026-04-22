# OpenAPI smoke checklist

- [ ] spec parses as OpenAPI 3.1.0
- [ ] all operationIds are unique
- [ ] all secured routes declare security
- [ ] all schemas set `additionalProperties: false` where appropriate
- [ ] examples match schemas
- [ ] error responses are standardized
- [ ] prod, staging, and dev servers are declared
