"""Reference FastAPI runtime for the OpenMythos contract."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from plugins.sha256_verifier.entrypoint import verify as verify_webhook_signature


@dataclass
class IdempotencyRecord:
    body_hash: str
    status_code: int
    response_body: dict[str, Any]
    expires_at: float


class InMemoryIdempotencyStore:
    """Redis-compatible shape for idempotency persistence."""

    def __init__(self, ttl_seconds: int = 60 * 60 * 24) -> None:
        self.ttl_seconds = ttl_seconds
        self._data: dict[str, IdempotencyRecord] = {}
        self._lock = Lock()

    def get(self, key: str) -> IdempotencyRecord | None:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if item and item.expires_at < now:
                self._data.pop(key, None)
                return None
            return item

    def set(self, key: str, body_hash: str, status_code: int, response_body: dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = IdempotencyRecord(
                body_hash=body_hash,
                status_code=status_code,
                response_body=response_body,
                expires_at=time.time() + self.ttl_seconds,
            )


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 120, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, principal: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            bucket = self._requests[principal]
            while bucket and (now - bucket[0]) > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False, 0
            bucket.append(now)
            return True, self.max_requests - len(bucket)


def _hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _scope_set(raw_scope: str | None) -> set[str]:
    return {s for s in (raw_scope or "").split() if s}


def require_scope(required: str):
    def validator(x_oauth_scopes: str | None = Header(default=None)) -> None:
        if required not in _scope_set(x_oauth_scopes):
            raise HTTPException(status_code=403, detail=f"Missing required OAuth2 scope: {required}")

    return validator


app = FastAPI(title="OpenMythos Runtime Reference", version="1.3.0")
idempotency_store = InMemoryIdempotencyStore()
rate_limiter = SlidingWindowRateLimiter()


@app.middleware("http")
async def enforce_rate_limit(request: Request, call_next):
    principal = request.headers.get("Authorization") or request.client.host or "anonymous"
    allowed, remaining = rate_limiter.check(principal)
    if not allowed:
        return JSONResponse(status_code=429, content={"error": "rate_limit_exceeded"})
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.middleware("http")
async def enforce_idempotency(request: Request, call_next):
    if request.method != "POST":
        return await call_next(request)

    key = request.headers.get("Idempotency-Key")
    if not key:
        return JSONResponse(status_code=400, content={"error": "missing_idempotency_key"})

    body = await request.body()
    body_hash = _hash_payload(body)
    existing = idempotency_store.get(key)
    if existing:
        if existing.body_hash != body_hash:
            return JSONResponse(status_code=409, content={"error": "idempotency_key_payload_mismatch"})
        return JSONResponse(status_code=existing.status_code, content=existing.response_body)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive
    response = await call_next(request)

    if 200 <= response.status_code < 300:
        raw = b""
        async for chunk in response.body_iterator:
            raw += chunk
        decoded = json.loads(raw.decode("utf-8")) if raw else {}
        idempotency_store.set(key, body_hash, response.status_code, decoded)
        return JSONResponse(status_code=response.status_code, content=decoded)
    return response


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orders", dependencies=[Depends(require_scope("orders:write"))])
async def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    return {"orderId": f"ord_{uuid4().hex[:10]}", "status": "accepted", "received": payload}


@app.post("/quantum/jobs", dependencies=[Depends(require_scope("quantum.jobs:write"))])
async def create_quantum_job(payload: dict[str, Any]) -> dict[str, Any]:
    return {"jobId": f"job_{uuid4().hex[:10]}", "status": "queued", "received": payload}


@app.post("/training/jobs", dependencies=[Depends(require_scope("training.jobs:write"))])
async def create_training_job(payload: dict[str, Any]) -> dict[str, Any]:
    return {"trainingId": f"train_{uuid4().hex[:10]}", "status": "queued", "received": payload}


@app.post("/webhooks/training/completed")
async def training_webhook(request: Request, x_webhook_signature: str | None = Header(default=None)) -> dict[str, str]:
    if not x_webhook_signature:
        raise HTTPException(status_code=400, detail="Missing X-Webhook-Signature header")

    secret = os.getenv("WEBHOOK_SECRET", "replace-me")
    payload = await request.body()
    if not verify_webhook_signature(secret=secret, payload=payload, provided_signature=x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    return {"status": "verified"}
