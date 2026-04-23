## Summary

-

## Validation

- [ ] `bash scripts/validate-openapi.sh`
- [ ] `python tests/plugins/run_registry_tests.py`
- [ ] `python tests/plugins/run_freeze_tests.py`
- [ ] `python tests/plugins/run_sha256_webhook_tests.py`
- [ ] `python tests/contract/run_contract_regression.py`

## Security Checklist

- [ ] No secrets/tokens added
- [ ] OAuth/idempotency/rate-limit impacts reviewed
- [ ] Webhook signature verification path covered
