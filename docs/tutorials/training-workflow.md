# Training Workflow Tutorial

This tutorial walks through a complete training job lifecycle.

## What you will do

1. Submit a training job
2. Poll job status until completion
3. Retrieve resulting metrics/artifact metadata
4. Freeze the training manifest for auditability

## 1) Configure runtime endpoint

```bash
export KATOPU_API_URL=http://localhost:8080
export KATOPU_API_KEY=dev-api-key
```

## 2) Run the lifecycle example

```bash
python3 examples/training-job-example.py
```

## 3) Understand terminal states

The example treats `completed`, `failed`, and `cancelled` as terminal states.
If the state is terminal, polling stops and the script fetches result payloads.

## 4) Freeze snapshots

The script calls the freeze endpoint to produce a deterministic hash over training metadata,
metrics, and artifact references.

## 5) Webhook notification extension

You can set `notificationWebhook` in the create request. For local development, pair this with:

```bash
python3 examples/webhook-integration-example.py
```

Then expose the local listener with a tunnel service and use that URL as your webhook target.
