# Getting Started Tutorial

This tutorial helps you run the OpenMythos Quantum API locally and execute your first API workflow.

## Prerequisites

- Python 3.11+
- `pip` and `venv`
- Optional: `uvicorn` for the reference runtime

## 1) Start the reference runtime

```bash
uvicorn runtime.server:app --host 0.0.0.0 --port 8080
```

## 2) Configure environment variables

In another terminal:

```bash
export KATOPU_API_URL=http://localhost:8080
export KATOPU_API_KEY=dev-api-key
```

## 3) Run the quickstart example

```bash
python3 examples/quickstart.py
```

This script demonstrates creating a training job, fetching its status, and listing recent jobs.

## 4) Run generated SDK examples (optional)

```bash
bash scripts/generate-clients.sh
python3 examples/generated-python-client-example.py
npx tsx examples/generated-typescript-client-example.ts
```

## Troubleshooting

- If you get `Connection refused`, verify `uvicorn` is running on port 8080.
- If you get a 401/403 response, check your API key header and auth requirements.
- See `docs/troubleshooting.md` for additional diagnostics.
