#!/usr/bin/env python3
"""Full training lifecycle example.

Flow:
1) Create training job
2) Poll status until terminal state
3) Fetch result artifact info
4) Freeze training manifest
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("KATOPU_API_URL", "http://localhost:8080")
API_KEY = os.environ.get("KATOPU_API_KEY", "dev-api-key")
POLL_INTERVAL_SECONDS = float(os.environ.get("TRAINING_POLL_INTERVAL_SECONDS", "5"))
MAX_POLLS = int(os.environ.get("TRAINING_MAX_POLLS", "60"))
TERMINAL_STATES = {"completed", "failed", "cancelled"}


def api_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_URL.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url=url, data=data, method=method)
    req.add_header("X-API-Key", API_KEY)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {details}") from exc


def main() -> None:
    create_payload = {
        "modelName": "gpt-4-turbo",
        "datasetId": "ds_fine_web_edu_10bt",
        "hyperparameters": {
            "epochs": 3,
            "batchSize": 32,
            "learningRate": 0.0001,
            "optimizer": "adamw",
        },
        "computeProfile": "baseline-medium",
        "notificationWebhook": "https://api.example.com/webhooks/training",
    }

    created = api_request("POST", "/training/jobs", create_payload)
    training_id = created.get("trainingId")
    if not training_id:
        raise RuntimeError("API did not return trainingId")

    print(f"Created training job: {training_id}")

    status = created.get("status", "queued")
    for poll in range(MAX_POLLS):
        if status in TERMINAL_STATES:
            break
        time.sleep(POLL_INTERVAL_SECONDS)
        snapshot = api_request("GET", f"/training/jobs/{training_id}")
        status = snapshot.get("status", "unknown")
        print(f"poll={poll + 1:02d} status={status}")

    result = api_request("GET", f"/training/jobs/{training_id}/results")
    print("Result payload:")
    print(json.dumps(result, indent=2))

    freeze_payload = {"includeMetrics": True, "includeArtifacts": True}
    freeze = api_request("POST", f"/freeze/training/jobs/{training_id}", freeze_payload)
    print("Freeze manifest:")
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
