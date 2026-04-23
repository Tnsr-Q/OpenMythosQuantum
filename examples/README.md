# Example Gallery

Runnable examples for common OpenMythos Quantum API workflows.

## API workflow examples

- `quickstart.py` — basic API usage for training endpoints
- `training-job-example.py` — full training lifecycle (create, poll, results, freeze)
- `circuit-optimization-example.py` — circuit creation + optimization + freeze snapshot
- `webhook-integration-example.py` — local webhook receiver with signature validation
- `plugin-development-example/` — sample plugin scaffold and descriptor

## Generated SDK examples

- `generated-python-client-example.py`
- `generated-typescript-client-example.ts`

Generate SDKs first:

```bash
bash scripts/generate-clients.sh
```

## Quick run

```bash
export KATOPU_API_URL=http://localhost:8080
export KATOPU_API_KEY=dev-api-key
python3 examples/quickstart.py
```
