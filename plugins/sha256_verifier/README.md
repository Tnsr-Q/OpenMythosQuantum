# SHA-256 Verifier Plugin

This plugin provides a custom entrypoint to verify webhook signatures.

## Entrypoint

`plugins/sha256_verifier/entrypoint.py`

## Usage

```bash
python3 plugins/sha256_verifier/entrypoint.py   --secret "$WEBHOOK_SIGNING_SECRET"   --signature "sha256=<hex>"   --payload-file /tmp/webhook.json
```

Expected output:
- `VERIFIED` (exit 0)
- `INVALID` (exit 1)
