#!/usr/bin/env python3
"""Quickstart example for basic API usage.

This script demonstrates:
1) Creating a training job
2) Fetching training job status
3) Listing training jobs

Set KATOPU_API_URL and KATOPU_API_KEY before running.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = os.environ.get("KATOPU_API_URL", "http://localhost:8080")
API_KEY = os.environ.get("KATOPU_API_KEY", "dev-api-key")


def request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_URL.rstrip('/')}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url=url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("X-API-Key", API_KEY)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            response_body = resp.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {details}") from exc


def main() -> None:
    print(f"Using API base URL: {API_URL}")

    create_payload = {
        "modelName": "gpt-4-turbo",
        "datasetId": "ds_fine_web_edu_10bt",
        "hyperparameters": {
            "epochs": 1,
            "batchSize": 8,
            "learningRate": 0.0001,
            "optimizer": "adamw",
        },
        "computeProfile": "baseline-medium",
    }

    created = request("POST", "/training/jobs", create_payload)
    training_id = created.get("trainingId")
    print("Created training job:", json.dumps(created, indent=2))

    if training_id:
        status = request("GET", f"/training/jobs/{training_id}")
        print("Training status:", json.dumps(status, indent=2))

    jobs = request("GET", "/training/jobs?limit=5")
    print("Recent training jobs:", json.dumps(jobs, indent=2))


if __name__ == "__main__":
    main()
