"""Helpers shared by plugin implementations."""

from __future__ import annotations

import time
from typing import Any


def now_ms() -> int:
    """Return Unix epoch milliseconds."""
    return int(time.time() * 1000)


def require_fields(payload: dict[str, Any], required: list[str]) -> None:
    """Raise ValueError if any required field is missing."""
    missing = [name for name in required if name not in payload]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
