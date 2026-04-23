# Security Policy

## Reporting a Vulnerability

If you discover a security issue, please report it privately:

1. **Do not** open a public GitHub issue.
2. Email: **security@katopu.example.com** with:
   - affected component(s)
   - reproduction steps / proof of concept
   - impact assessment (confidentiality, integrity, availability)
   - suggested mitigation (if available)
3. If email is unavailable, open a private security advisory in GitHub Security Advisories.

### Response Targets

- Acknowledgement: **within 2 business days**
- Triage and severity classification: **within 5 business days**
- Initial remediation plan: **within 10 business days**

## Security Update Policy

Security fixes are prioritized by severity:

- **Critical:** patch and release as soon as possible (target within 48 hours)
- **High:** patch in the next patch release cycle (target within 7 days)
- **Medium:** patch in the next scheduled release
- **Low:** best-effort, usually batched into routine maintenance

Backported fixes are provided for all supported versions listed below.

## Supported Versions

| Version | Supported | Notes |
|---|---|---|
| 1.2.x | ✅ | Active development and security fixes |
| 1.1.x | ✅ | Security and critical bug fixes only |
| 1.0.x | ⚠️ | Limited support; migration recommended |
| < 1.0 | ❌ | Unsupported |

## Security Controls in This Repository

- OpenAPI contract-level security requirements and webhook signature schemas
- Runtime reference checks for idempotency, OAuth scopes, and webhook signature verification
- CI secret scanning (Gitleaks + detect-secrets)
- CI SBOM generation and artifact upload
- Baseline security configuration validation via `scripts/security-baseline-check.py`
